"""CSS stylesheet for FleetDashboardApp.

Extracted to keep the main dashboard module under 300 lines.
"""

APP_CSS = """
Screen {
    layout: vertical;
    background: $surface;
}

/* ---- Pirate Logo ---- */
#pirate-logo {
    height: auto;
    max-height: 10;
    padding: 0 2;
    content-align: center middle;
    text-align: center;
    background: $surface;
}
#pirate-logo.hidden {
    display: none;
}

/* ---- Fleet Overview Tab ---- */
#fleet-tab Horizontal {
    height: 1fr;
}
#session-table {
    width: 62%;
    border: tall $primary-background;
    scrollbar-size: 1 1;
}
#session-table > .datatable--cursor {
    background: $accent 40%;
    color: $text;
}
#preview-pane {
    width: 38%;
    border: tall $accent;
    padding: 0 1;
    background: $panel;
    color: $text-muted;
}
#all-session-table {
    width: 62%;
    border: tall $primary-background;
    scrollbar-size: 1 1;
}
#all-session-table > .datatable--cursor {
    background: $accent 40%;
    color: $text;
}
#all-preview-pane {
    width: 38%;
    border: tall $accent;
    padding: 0 1;
    background: $panel;
    color: $text-muted;
}
#fleet-summary {
    height: 3;
    dock: bottom;
    padding: 0 2;
    background: $primary-background;
    color: $text;
    text-style: bold;
}

/* ---- Session Detail Tab ---- */
#detail-header {
    height: auto;
    max-height: 6;
    padding: 1 2;
    background: $primary-background;
    color: $text;
    text-style: bold;
    border-bottom: heavy $accent;
}
#tmux-capture {
    height: 1fr;
    min-height: 10;
    border: tall $primary;
    padding: 0 1;
    background: #1a1a2e;
    color: #eaeaea;
}
#proposal-section {
    height: auto;
    max-height: 16;
    border: tall $warning;
    padding: 1 2;
    background: $panel;
}

/* ---- Action Editor Tab ---- */
#editor-reasoning {
    height: auto;
    max-height: 8;
    padding: 1 2;
    background: $panel;
    border: tall $accent;
    color: $text-muted;
}
#input-editor {
    height: 10;
    border: tall $success;
}
#action-select {
    margin: 1 2;
    width: 40;
}

/* ---- Projects Tab ---- */
#project-add-bar {
    height: auto;
    layout: horizontal;
    padding: 1 1;
    background: $primary-background;
}
#project-repo-input {
    width: 1fr;
    margin: 0 1 0 0;
}
#project-table {
    height: 1fr;
    border: tall $primary-background;
    scrollbar-size: 1 1;
}
#project-table > .datatable--cursor {
    background: $accent 40%;
    color: $text;
}

/* ---- New Session Tab ---- */
#new-session-header {
    padding: 1 2;
    background: $primary-background;
    color: $text;
}
#new-session-form {
    height: auto;
    padding: 1 2;
    align: left middle;
}
#new-session-form Select {
    width: 30;
    margin: 0 1;
}

/* ---- Shared ---- */
Button {
    margin: 0 1;
    min-width: 14;
}
.button-row {
    height: 5;
    layout: horizontal;
    align: center middle;
    padding: 1 0;
}
#loading-overlay {
    display: none;
    dock: top;
    height: 3;
    content-align: center middle;
    background: $warning 30%;
}
.active-loading #loading-overlay {
    display: block;
}

/* ---- Tab styling ---- */
TabbedContent {
    height: 1fr;
}
TabPane {
    padding: 0;
}
"""
