import json

from amplihack.eval.gherkin_prompt_experiment import (
    default_gherkin_manifest_path,
    evaluate_gherkin_artifact,
    load_gherkin_manifest,
    main,
)


def test_default_manifest_path_points_to_gherkin_experiment_home():
    manifest_path = default_gherkin_manifest_path()
    assert manifest_path.name == "manifest.json"
    assert "experiments/hive_mind/gherkin_prompt_language" in str(manifest_path)


def test_gherkin_manifest_loads_and_validates():
    manifest = load_gherkin_manifest()
    assert manifest.experiment_id == "gherkin-prompt-language-v1"
    assert manifest.experiment_home == "experiments/hive_mind/gherkin_prompt_language"
    assert manifest.generation_target.target_id == "user_authentication_api"


def test_gherkin_manifest_resolves_spec_and_prompt_assets():
    manifest = load_gherkin_manifest()
    spec_path = manifest.resolve_asset_path(manifest.spec_asset)
    assert spec_path.name == "user_authentication.feature"
    assert spec_path.exists()
    for prompt_variant in manifest.prompt_variants:
        assert manifest.resolve_asset_path(prompt_variant.path).exists()


def test_expand_smoke_matrix_returns_eight_conditions():
    manifest = load_gherkin_manifest()
    conditions = manifest.expand_matrix(smoke=True)
    assert len(conditions) == 8
    assert {item.repeat_index for item in conditions} == {1}
    assert {item.prompt_variant_id for item in conditions} == {
        "english",
        "gherkin_only",
        "gherkin_plus_english",
        "gherkin_plus_acceptance",
    }
    assert {item.model_id for item in conditions} == {"claude-opus-4.6", "gpt-5.4"}


def test_expand_full_matrix_uses_full_repeat_count():
    manifest = load_gherkin_manifest()
    conditions = manifest.expand_matrix(smoke=False)
    assert len(conditions) == 24
    assert {item.repeat_index for item in conditions} == {1, 2, 3}


def test_prompt_bundle_appends_gherkin_spec_for_spec_variants():
    manifest = load_gherkin_manifest()
    english_bundle = manifest.load_prompt_bundle("english")
    gherkin_bundle = manifest.load_prompt_bundle("gherkin_only")

    assert "Formal specification" not in english_bundle.combined_text()
    assert "Feature: User Authentication" not in english_bundle.combined_text()

    combined = gherkin_bundle.combined_text()
    assert "Formal specification" in combined
    assert "Feature: User Authentication" in combined


def test_evaluate_full_artifact_scores_high():
    """A comprehensive artifact covering all scenarios should score near 1.0."""
    artifact = """
from flask import Flask, request, jsonify
import bcrypt, jwt, datetime, uuid

app = Flask(__name__)
users = {}
failed_attempts = {}
refresh_tokens = {}

@app.route('/register', methods=['POST'])
def register():
    email = request.json['email']
    password = request.json['password']
    if '@' not in email:
        return jsonify({'error': 'invalid email'}), 400
    if email in users:
        return jsonify({'error': 'email already registered'}), 409
    if len(password) < 8:
        return jsonify({'error': 'password too weak'}), 400
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user_id = str(uuid.uuid4())
    users[email] = {'id': user_id, 'password_hash': password_hash}
    return jsonify({'id': user_id}), 201

@app.route('/login', methods=['POST'])
def login():
    email = request.json['email']
    password = request.json['password']
    if failed_attempts.get(email, 0) >= 5:
        return jsonify({'error': 'account locked'}), 423
    user = users.get(email)
    if not user or not bcrypt.checkpw(password.encode(), user['password_hash']):
        failed_attempts[email] = failed_attempts.get(email, 0) + 1
        return jsonify({'error': 'invalid credentials'}), 401
    access_token = jwt.encode({'sub': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, 'secret')
    refresh_token = str(uuid.uuid4())
    refresh_tokens[refresh_token] = user['id']
    return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200

@app.route('/refresh', methods=['POST'])
def refresh():
    token = request.json.get('refresh_token')
    if token not in refresh_tokens:
        return jsonify({'error': 'refresh token expired'}), 401
    return jsonify({'access_token': 'new_token'}), 200

@app.route('/me', methods=['GET'])
def get_me():
    auth = request.headers.get('Authorization')
    if not auth:
        return jsonify({'error': 'missing authorization'}), 401
    try:
        payload = jwt.decode(auth.split()[1], 'secret', algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'token expired'}), 401
    return jsonify({'email': 'test@example.com', 'id': payload['sub']}), 200

import pytest

def test_register_success(client):
    response = client.post('/register', json={'email': 'a@b.com', 'password': 'Str0ng!Pass'})
    assert response.status_code == 201

def test_login_success(client):
    response = client.post('/login', json={'email': 'a@b.com', 'password': 'Str0ng!Pass'})
    assert 'access_token' in response.json

def test_account_lockout(client):
    for _ in range(5):
        client.post('/login', json={'email': 'a@b.com', 'password': 'wrong'})  # pragma: allowlist secret
    assert client.post('/login', json={'email': 'a@b.com', 'password': 'Str0ng!Pass'}).status_code == 423  # pragma: allowlist secret
"""
    evaluation = evaluate_gherkin_artifact(artifact)
    assert evaluation.metrics.baseline_score >= 0.8
    assert evaluation.metrics.invariant_compliance >= 0.8
    assert evaluation.metrics.proof_alignment == 1.0  # has implementation
    assert evaluation.metrics.local_protocol_alignment == 1.0  # has tests


def test_evaluate_empty_artifact_scores_zero():
    """An empty artifact should score 0.0 across the board."""
    evaluation = evaluate_gherkin_artifact("")
    assert evaluation.metrics.baseline_score == 0.0
    assert evaluation.metrics.invariant_compliance == 0.0
    assert evaluation.metrics.proof_alignment == 0.0
    assert evaluation.metrics.local_protocol_alignment == 0.0


def test_evaluate_partial_artifact_scores_proportionally():
    """An artifact with only registration should score partially."""
    artifact = """
from flask import Flask, request, jsonify
import bcrypt

app = Flask(__name__)
users = {}

@app.route('/register', methods=['POST'])
def register():
    email = request.json['email']
    password = request.json['password']
    if email in users:
        return jsonify({'error': 'email already registered'}), 409
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    users[email] = {'password_hash': password_hash}
    return jsonify({'id': '123'}), 201
"""
    evaluation = evaluate_gherkin_artifact(artifact)
    assert 0.0 < evaluation.metrics.baseline_score < 1.0
    assert evaluation.checks["password_hashing"] is True
    assert evaluation.checks["duplicate_email_rejection"] is True
    assert evaluation.checks["login_endpoint"] is False


def test_cli_prints_matrix_json(capsys):
    result = main([])
    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["experiment_id"] == "gherkin-prompt-language-v1"
    assert output["target_id"] == "user_authentication_api"
    assert len(output["conditions"]) == 24  # full matrix


def test_cli_smoke_matrix(capsys):
    result = main(["--smoke"])
    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output["conditions"]) == 8


def test_cli_variant_prints_prompt(capsys):
    result = main(["--variant", "gherkin_only"])
    assert result == 0
    output = capsys.readouterr().out
    assert "User Authentication REST API" in output
    assert "Feature: User Authentication" in output
