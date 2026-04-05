const { app } = window.comfyAPI.app;
const { api } = window.comfyAPI.api;
const { ComfyDialog } = window.comfyAPI.ui;

const EXTENSION_NAME = "Mutiny.Settings";
const API_ROOT = "/mutiny";
const DISCORD_ID_GUIDE_URL =
    "https://github.com/Artificial-Sweetener/ComfyUI-Mutiny/blob/main/docs/discord-ids.md";

function createElement(tagName, attributes = {}, children = []) {
    const element = document.createElement(tagName);

    for (const [name, value] of Object.entries(attributes)) {
        if (name === "className") {
            element.className = value;
            continue;
        }
        if (name === "textContent") {
            element.textContent = value;
            continue;
        }
        if (name === "type") {
            element.type = value;
            continue;
        }
        if (name === "value") {
            element.value = value;
            continue;
        }
        if (name === "checked") {
            element.checked = value;
            continue;
        }
        if (name === "disabled") {
            element.disabled = value;
            continue;
        }
        if (name.startsWith("on") && typeof value === "function") {
            element.addEventListener(name.slice(2).toLowerCase(), value);
            continue;
        }
        if (value !== undefined && value !== null) {
            element.setAttribute(name, value);
        }
    }

    for (const child of children) {
        if (child instanceof Node) {
            element.appendChild(child);
            continue;
        }
        if (child !== undefined && child !== null) {
            element.appendChild(document.createTextNode(String(child)));
        }
    }

    return element;
}

function createSvgElement(tagName, attributes = {}) {
    const element = document.createElementNS(
        "http://www.w3.org/2000/svg",
        tagName,
    );

    for (const [name, value] of Object.entries(attributes)) {
        if (name === "className") {
            element.setAttribute("class", value);
            continue;
        }
        if (value !== undefined && value !== null) {
            element.setAttribute(name, value);
        }
    }

    return element;
}

function createButton(label, { kind = "primary", onClick } = {}) {
    const classNames = ["p-button", "p-component", "p-button-sm"];
    if (kind !== "primary") {
        classNames.push("p-button-text", "p-button-secondary");
    }

    return createElement(
        "button",
        {
            className: classNames.join(" "),
            type: "button",
            onclick: onClick,
        },
        [
            createElement("span", {
                className: "p-button-label",
                textContent: label,
            }),
        ],
    );
}

function setButtonLabel(button, label) {
    const labelElement = button.querySelector(".p-button-label");
    if (labelElement) {
        labelElement.textContent = label;
    }
}

function measureNaturalButtonWidth({ kind, labels }) {
    const probeHost = createElement("div", {
        style: [
            "position:absolute",
            "visibility:hidden",
            "pointer-events:none",
            "left:-9999px",
            "top:0",
        ].join(";"),
    });
    document.body.appendChild(probeHost);

    let maxWidth = 0;
    for (const label of labels) {
        const button = createButton(label, { kind });
        probeHost.appendChild(button);
        maxWidth = Math.max(maxWidth, button.getBoundingClientRect().width);
    }

    probeHost.remove();
    return Math.ceil(maxWidth);
}

function buildMaskedTextInputAttributes(overrides = {}) {
    return {
        type: "text",
        autocomplete: "off",
        autocapitalize: "off",
        spellcheck: "false",
        "data-1p-ignore": "true",
        "data-lpignore": "true",
        "data-bwignore": "true",
        "data-masked": "true",
        ...overrides,
    };
}

function getErrorMessage(error, fallbackMessage) {
    if (error instanceof Error && error.message) {
        return error.message;
    }
    return fallbackMessage;
}

function addToast({ severity, summary, detail }) {
    app.extensionManager?.toast?.add({ severity, summary, detail });
}

function showErrorToast(summary, error, fallbackDetail) {
    addToast({
        severity: "error",
        summary,
        detail: getErrorMessage(error, fallbackDetail),
    });
}

function showSuccessToast(summary, detail) {
    addToast({
        severity: "success",
        summary,
        detail,
    });
}

async function fetchJson(path, options = {}) {
    const response = await api.fetchApi(path, {
        cache: "no-store",
        ...options,
    });

    let payload = {};
    const bodyText = await response.text();
    if (bodyText) {
        try {
            payload = JSON.parse(bodyText);
        } catch {
            payload = {};
        }
    }

    if (!response.ok) {
        throw new Error(
            payload.error || `Request failed with status ${response.status}.`,
        );
    }

    return payload;
}

function createDefaultSnapshot() {
    return {
        discord: {
            guildId: "",
            channelId: "",
            tokenConfigured: false,
            apiEndpoint: "",
        },
        cache: {
            artifactCacheRamMaxMb: 32,
            diskCacheMaxMb: 256,
            diskUsage: {
                usedBytes: 0,
                maxBytes: 256 * 1024 * 1024,
                percentUsed: 0,
            },
        },
        runtime: {
            taskTimeoutMinutes: 5,
        },
    };
}

function normalizeSettingsStatus(payload = {}) {
    const settings = payload.settings || {};
    const discord = settings.discord || {};
    const cacheSettings = settings.cache || {};
    const executionSettings = settings.engine?.execution || {};

    return {
        discord: {
            guildId: discord.guild_id || "",
            channelId: discord.channel_id || "",
            tokenConfigured: Boolean(payload.token_configured),
            apiEndpoint: discord.api_endpoint || "",
        },
        cache: {
            artifactCacheRamMaxMb:
                cacheSettings.artifact_cache_ram_max_mb ?? 32,
            diskCacheMaxMb: cacheSettings.disk_cache_max_mb ?? 256,
            diskUsage: {
                usedBytes: 0,
                maxBytes:
                    (cacheSettings.disk_cache_max_mb ?? 256) * 1024 * 1024,
                percentUsed: 0,
            },
        },
        runtime: {
            taskTimeoutMinutes: executionSettings.task_timeout_minutes ?? 5,
        },
    };
}

function formatMegabytes(byteCount) {
    return `${(byteCount / (1024 * 1024)).toFixed(2)} MB`;
}

function installStyleSheet() {
    if (document.getElementById("mutiny-settings-style")) {
        return;
    }

    const style = createElement("style", {
        id: "mutiny-settings-style",
        textContent: `
            :root {
                --mutiny-settings-inline-gap: 0.5rem;
                --mutiny-settings-explainer-width: 80%;
            }

            .mutiny-settings-field,
            .mutiny-settings-token-row {
                display: flex;
                justify-content: flex-end;
                max-width: 100%;
                margin-left: auto;
            }

            .mutiny-settings-token-row {
                align-items: center;
                gap: 0.5rem;
                flex-wrap: wrap;
            }

            .mutiny-settings-input {
                flex: 1 1 auto;
                min-width: 0;
            }

            .mutiny-settings-control-stack {
                display: flex;
                flex-direction: column;
                gap: 0.35rem;
                width: 100%;
            }

            .mutiny-settings-help,
            .mutiny-settings-note,
            .mutiny-settings-section-note {
                color: var(--descrip-text);
                font-size: 0.82rem;
                line-height: 1.45;
            }

            .mutiny-settings-note {
                inline-size: var(--mutiny-settings-explainer-width);
                max-inline-size: var(--mutiny-settings-explainer-width);
                min-inline-size: 0;
                overflow-wrap: anywhere;
            }

            .mutiny-settings-section-note {
                inline-size: var(--mutiny-settings-explainer-width);
                max-inline-size: var(--mutiny-settings-explainer-width);
                min-inline-size: 0;
                margin: -0.5rem 0 1rem;
                overflow-wrap: anywhere;
            }

            .mutiny-settings-note a,
            .mutiny-settings-section-note a {
                color: var(--p-primary-color, var(--fg-color));
                text-decoration: underline;
            }

            .mutiny-settings-note strong,
            .mutiny-settings-section-note strong {
                color: var(--fg-color);
                font-weight: 700;
            }

            .mutiny-settings-meter {
                display: flex;
                flex-direction: column;
                gap: 0.35rem;
            }

            .mutiny-settings-meter[data-display="wide"] {
                width: min(55%, 36rem);
                min-width: 20rem;
                max-width: 100%;
                margin: 0 auto;
            }

            .mutiny-settings-meter-bar {
                width: 100%;
                height: 0.55rem;
                overflow: hidden;
                background: color-mix(in srgb, var(--comfy-input-bg) 70%, black);
                border: 1px solid var(--border-color);
                border-radius: 999px;
            }

            .mutiny-settings-meter-fill {
                height: 100%;
                background: linear-gradient(90deg, #5b8cff 0%, #7fd1ff 100%);
                border-radius: 999px;
                transition: width 160ms ease;
            }

            .mutiny-settings-footer {
                display: flex;
                flex: 0 0 auto;
                flex-direction: column;
                gap: 0.6rem;
                padding: 0.8rem 1.5rem 1rem;
                border-top: 1px solid var(--border-color);
                align-items: center;
            }

            .mutiny-settings-footer-copy {
                color: var(--descrip-text);
                font-size: 0.78rem;
                line-height: 1.45;
                text-align: center;
            }

            .mutiny-settings-footer-links {
                display: flex;
                gap: 0.4rem;
                flex-wrap: wrap;
                justify-content: center;
            }

            .mutiny-settings-footer-button {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.34rem;
                min-width: 0;
                padding: 0.34rem 0.56rem;
                border: 1px solid var(--border-color);
                border-radius: 12px;
                color: var(--fg-color);
                font-size: 0.73rem;
                font-weight: 600;
                line-height: 1;
                white-space: nowrap;
                text-decoration: none;
                background: color-mix(in srgb, var(--comfy-input-bg) 82%, white);
                transition:
                    transform 120ms ease,
                    border-color 120ms ease,
                    background 120ms ease;
            }

            .mutiny-settings-footer-button-icon {
                width: 0.72rem;
                height: 0.72rem;
                flex: 0 0 auto;
            }

            .mutiny-settings-footer-button:hover {
                transform: translateY(-1px);
                border-color: color-mix(
                    in srgb,
                    var(--p-primary-color, #5b8cff) 45%,
                    var(--border-color)
                );
                background: color-mix(
                    in srgb,
                    var(--comfy-input-bg) 62%,
                    white
                );
            }

            .mutiny-settings-footer-button[data-brand="website"] {
                border-color: color-mix(
                    in srgb,
                    var(--p-primary-color, #5b8cff) 35%,
                    var(--border-color)
                );
            }

            .mutiny-settings-footer-button[data-brand="github"] {
                border-color: color-mix(in srgb, #6e7681 55%, var(--border-color));
            }

            .mutiny-settings-footer-button[data-brand="kofi"] {
                border-color: color-mix(in srgb, #29abe0 55%, var(--border-color));
            }

            .mutiny-settings-footer-button[data-brand="patreon"] {
                border-color: color-mix(in srgb, #ff424d 55%, var(--border-color));
            }

            .mutiny-settings-input[data-masked="true"],
            .mutiny-token-dialog-input[data-masked="true"] {
                -webkit-text-security: disc;
            }

            .mutiny-settings-field[data-maskable="true"] {
                align-items: center;
                gap: var(--mutiny-settings-inline-gap);
            }

            .mutiny-settings-field[data-maskable="true"] .mutiny-settings-input {
                flex: 1 1 auto;
            }

            .mutiny-settings-field [data-reveal-toggle="true"] {
                flex: 0 0 auto;
                justify-content: center;
            }

            .mutiny-settings-token-row [data-token-primary="true"] {
                flex: 1 1 auto;
                justify-content: center;
            }

            .mutiny-settings-field[data-pending="true"],
            .mutiny-settings-token-row[data-pending="true"] {
                opacity: 0.8;
            }

            .mutiny-settings-token-row .p-button {
                white-space: nowrap;
            }

            .mutiny-token-dialog {
                inset: 0;
                max-width: none;
                max-height: none;
                padding: 1.5rem;
                transform: none;
                align-items: center;
                justify-content: center;
                background: rgba(5, 10, 18, 0.52);
                border: none;
                border-radius: 0;
                box-shadow: none;
                color: var(--fg-color);
                font-family: var(--font-family, Arial, sans-serif);
                font-size: 0.95rem;
                z-index: 2147483647;
            }

            .mutiny-token-dialog-text {
                display: contents;
                margin: 0;
                overflow: visible;
                white-space: normal;
            }

            .mutiny-token-dialog .comfy-modal-content {
                display: flex;
                flex-direction: column;
                gap: 0.95rem;
                width: min(36rem, calc(100vw - 2rem));
                max-height: calc(100vh - 3rem);
                padding: 1.15rem;
                overflow: auto;
                background: var(--comfy-menu-bg);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                box-shadow: 0 28px 80px rgba(0, 0, 0, 0.45);
            }

            .mutiny-token-dialog-body {
                display: flex;
                flex-direction: column;
                gap: 0.9rem;
            }

            .mutiny-token-dialog-title {
                margin: 0;
                font-size: 1rem;
            }

            .mutiny-token-dialog-copy {
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }

            .mutiny-token-dialog-copy p {
                margin: 0;
                line-height: 1.45;
            }

            .mutiny-token-dialog-field {
                display: flex;
                flex-direction: column;
                gap: 0.375rem;
            }

            .mutiny-token-dialog-label {
                color: var(--descrip-text);
                font-size: 0.82rem;
            }

            .mutiny-token-dialog-input {
                width: 100%;
            }

            .mutiny-token-dialog-actions {
                display: flex;
                justify-content: flex-end;
                gap: 0.6rem;
                flex-wrap: wrap;
            }

            .mutiny-token-dialog-actions .p-button {
                min-width: 8.75rem;
            }
        `,
    });

    document.head.appendChild(style);
}

class MutinySettingsLayoutCoordinator {
    constructor() {
        this.discordRows = new Set();
        this.displayRows = new Map();
        this.syncQueued = false;
        this.revealButtonWidth = 0;

        window.addEventListener("resize", () => {
            this.scheduleLayoutSync();
        });

        observeBodyMutations(() => {
            this.scheduleLayoutSync();
        });
    }

    registerDiscordRow(row) {
        this.discordRows.add(row);
        this.scheduleLayoutSync();
    }

    registerDisplayRow(rootElement, options = {}) {
        this.displayRows.set(rootElement, {
            pullUp: false,
            centerContent: false,
            ...options,
        });
        this.scheduleLayoutSync();
    }

    scheduleDiscordWidthSync() {
        this.scheduleLayoutSync();
    }

    scheduleLayoutSync() {
        if (this.syncQueued) {
            return;
        }

        this.syncQueued = true;
        window.requestAnimationFrame(() => {
            this.syncQueued = false;
            this.syncDisplayRows();
            this.syncDiscordControlWidths();
        });
    }

    syncDisplayRows() {
        for (const [rootElement, options] of this.displayRows.entries()) {
            if (!rootElement.isConnected) {
                continue;
            }

            this.applyDisplayRowLayout(rootElement, options);
        }
    }

    applyDisplayRowLayout(
        rootElement,
        { pullUp = false, centerContent = false } = {},
    ) {
        const formInput = rootElement.closest(".form-input");
        const row = formInput?.parentElement;
        const formLabel = row?.querySelector(".form-label");

        if (!formInput || !row || !formLabel) {
            return;
        }

        row.style.alignItems = "flex-start";
        row.style.gap = "0";
        row.style.marginTop = pullUp ? "-0.5rem" : "";
        row.style.justifyContent = centerContent ? "center" : "";
        formLabel.style.display = "none";
        formInput.style.flex = "1 1 100%";
        formInput.style.width = "100%";
        formInput.style.margin = centerContent ? "0 auto" : "0";
        formInput.style.justifyContent = centerContent
            ? "center"
            : "flex-start";
    }

    syncDiscordControlWidths() {
        const rows = [...this.discordRows].filter((row) => row.isConnected);
        if (!rows.length) {
            return;
        }

        if (!this.revealButtonWidth) {
            this.revealButtonWidth = measureNaturalButtonWidth({
                kind: "secondary",
                labels: ["Show", "Hide"],
            });
        }

        for (const row of rows) {
            row.style.width = "";
            for (const revealButton of row.querySelectorAll(
                '[data-reveal-toggle="true"]',
            )) {
                revealButton.style.width = `${this.revealButtonWidth}px`;
            }
        }

        const widestControlSpan = Math.max(
            ...rows.map((row) => this.measureRowControlSpan(row)),
        );

        for (const row of rows) {
            row.style.width = `${widestControlSpan}px`;
        }
    }

    measureRowControlSpan(row) {
        const children = [...row.children].filter(
            (child) => child.getBoundingClientRect().width > 0,
        );
        if (!children.length) {
            return 0;
        }

        const rowStyle = window.getComputedStyle(row);
        const gapValue = rowStyle.columnGap || rowStyle.gap || "0px";
        const gap = Number.parseFloat(gapValue) || 0;

        const childWidth = children.reduce(
            (total, child) => total + child.getBoundingClientRect().width,
            0,
        );
        return Math.ceil(childWidth + gap * Math.max(children.length - 1, 0));
    }
}

const TOKEN_DIALOG_CONTENT = {
    add: {
        title: "Add Discord Token",
        fieldLabel: "Discord Token",
        submitLabel: "Store Token",
        errorSummary: "Failed to store Discord Token.",
        errorDetail: "Unable to store the Discord token.",
        descriptionLines: [
            "Mutiny requires a Discord token to operate.",
            "Your token will be stored securely in your system credential store.",
            "After it is stored here, Mutiny will not display the token back to you, and it should not be retrievable from this interface.",
            "Do not keep your token in plaintext files, notes, screenshots, or scripts. Remove any insecure copies after storing it here.",
            "If your Discord token is exposed, someone else may be able to access your Discord account.",
            "Mutiny does not provide instructions for obtaining a Discord token. If you need that information, find it separately.",
        ],
    },
    replace: {
        title: "Replace Discord Token",
        fieldLabel: "New Discord Token",
        submitLabel: "Replace Token",
        errorSummary: "Failed to replace Discord Token.",
        errorDetail: "Unable to replace the Discord token.",
        descriptionLines: [
            "Mutiny requires a Discord token to operate.",
            "Your token is stored securely in your system credential store.",
            "Mutiny does not display the stored token back to you, and it should not be retrievable from this interface.",
            "If you need to change the token, you must replace it by entering a new one here.",
            "Do not keep your token in plaintext files, notes, screenshots, or scripts. Remove any insecure copies after storing it here.",
            "If your Discord token is exposed, someone else may be able to access your Discord account.",
            "Mutiny does not provide instructions for obtaining a Discord token. If you need that information, find it separately.",
        ],
    },
    clear: {
        title: "Clear Discord Token",
        submitLabel: "Clear Token",
        errorSummary: "Failed to clear Discord Token.",
        errorDetail: "Unable to clear the Discord token.",
        descriptionLines: [
            "This will remove the stored Discord token from Mutiny's system credential store entry.",
            "Mutiny will not operate again until a new Discord token is stored.",
        ],
    },
};

const MUTINY_SETUP_ERROR_MESSAGES = {
    missingGuildId:
        "Mutiny needs your Discord guild ID before it can run. Add it in ComfyUI Settings under Mutiny, and see the settings panel for instructions.",
    missingChannelId:
        "Mutiny needs your Discord channel ID before it can run. Add it in ComfyUI Settings under Mutiny, and see the settings panel for instructions.",
    missingToken:
        "Mutiny needs your Discord token before it can run. Save it in ComfyUI Settings under Mutiny. You'll need to figure out how to obtain that yourself; Mutiny does not provide help with token acquisition.",
};

function openExternalLink(url) {
    window.open(url, "_blank", "noopener,noreferrer");
}

async function readMutinyMissingSetupState(apiClient) {
    const payload = await apiClient.loadSettings();
    const status = normalizeSettingsStatus(payload);
    return {
        guildIdMissing: !status.discord.guildId.trim(),
        channelIdMissing: !status.discord.channelId.trim(),
        tokenMissing: !status.discord.tokenConfigured,
    };
}

function inferMutinyMissingSetupStateFromMessage(message) {
    const normalized = String(message || "").trim();
    return {
        guildIdMissing:
            normalized === MUTINY_SETUP_ERROR_MESSAGES.missingGuildId,
        channelIdMissing:
            normalized === MUTINY_SETUP_ERROR_MESSAGES.missingChannelId,
        tokenMissing: normalized === MUTINY_SETUP_ERROR_MESSAGES.missingToken,
    };
}

function isMutinyMissingSetupMessage(message) {
    const normalized = String(message || "").trim();
    return Object.values(MUTINY_SETUP_ERROR_MESSAGES).includes(normalized);
}

function createMutinySetupDialogContent(missingState) {
    const missingLabels = [];
    if (missingState.guildIdMissing) {
        missingLabels.push("Guild ID");
    }
    if (missingState.channelIdMissing) {
        missingLabels.push("Channel ID");
    }
    if (missingState.tokenMissing) {
        missingLabels.push("Discord token");
    }

    let identityGuidance = null;
    if (missingState.guildIdMissing && missingState.channelIdMissing) {
        identityGuidance =
            "Add your Guild ID and Channel ID in ComfyUI Settings under Mutiny. See the settings panel for instructions.";
    } else if (missingState.guildIdMissing) {
        identityGuidance =
            "Add your Guild ID in ComfyUI Settings under Mutiny. See the settings panel for instructions.";
    } else if (missingState.channelIdMissing) {
        identityGuidance =
            "Add your Channel ID in ComfyUI Settings under Mutiny. See the settings panel for instructions.";
    }

    const children = [
        createElement("h3", {
            className: "mutiny-token-dialog-title",
            textContent: "Mutiny Setup Required",
        }),
        createElement("div", { className: "mutiny-token-dialog-copy" }, [
            createElement("p", {
                textContent:
                    "Mutiny is missing required Discord configuration and cannot run yet.",
            }),
            createElement("p", {
                textContent: missingLabels.length
                    ? `Missing: ${missingLabels.join(", ")}.`
                    : "Open ComfyUI Settings and finish the Mutiny setup.",
            }),
        ]),
    ];

    if (identityGuidance) {
        children[1].appendChild(
            createElement("p", {
                textContent: identityGuidance,
            }),
        );
        children[1].appendChild(
            createElement("p", {
                textContent:
                    "If you still need help finding your Guild ID or Channel ID, use the setup guide below.",
            }),
        );
    }

    if (missingState.tokenMissing) {
        children[1].appendChild(
            createElement("p", {
                textContent:
                    "Add your Discord token in ComfyUI Settings under Mutiny. You'll need to figure out how to obtain that yourself; Mutiny does not provide help with token acquisition.",
            }),
        );
    }

    return createElement(
        "div",
        { className: "mutiny-token-dialog-body" },
        children,
    );
}

function openMutinySetupRequiredDialog(missingState, { onClose } = {}) {
    const dialog = new ComfyDialog("div", []);
    dialog.element.classList.add("comfy-dialog", "mutiny-token-dialog");
    dialog.textElement.classList.add("mutiny-token-dialog-text");

    const closeDialog = () => {
        dialog.close();
        dialog.element.remove();
        onClose?.();
    };

    const closeButton = createButton("Close", {
        kind: "secondary",
        onClick: closeDialog,
    });
    const guideButton = createButton("Open Setup Guide", {
        onClick: () => {
            openExternalLink(DISCORD_ID_GUIDE_URL);
        },
    });

    const content = createMutinySetupDialogContent(missingState);
    content.appendChild(
        createElement("div", { className: "mutiny-token-dialog-actions" }, [
            closeButton,
            guideButton,
        ]),
    );

    dialog.show(content);
    document.body.appendChild(dialog.element);
    dialog.element.style.zIndex = "2147483647";
    return dialog;
}

function openMutinyDialog({
    title,
    descriptionLines,
    fieldLabel,
    submitLabel,
    errorSummary,
    errorDetail,
    onSubmit,
    onClose,
}) {
    let pending = false;

    const input =
        fieldLabel === undefined
            ? null
            : createElement(
                  "input",
                  buildMaskedTextInputAttributes({
                      className:
                          "mutiny-token-dialog-input p-inputtext p-component",
                  }),
              );

    const closeDialog = () => {
        if (input) {
            input.value = "";
        }
        dialog.close();
        dialog.element.remove();
        onClose?.();
    };

    const cancelButton = createButton("Cancel", {
        kind: "secondary",
        onClick: closeDialog,
    });
    const submitButton = createButton(submitLabel, {
        onClick: () => {
            void handleSubmit();
        },
    });
    const dialog = new ComfyDialog("div", []);
    dialog.element.classList.add("comfy-dialog", "mutiny-token-dialog");
    dialog.textElement.classList.add("mutiny-token-dialog-text");

    const updateControls = () => {
        const hasValue = input ? input.value.trim().length > 0 : true;

        if (input) {
            input.disabled = pending;
        }

        submitButton.disabled = pending || !hasValue;
        cancelButton.disabled = pending;
    };

    const handleSubmit = async () => {
        const submittedValue = input ? input.value.trim() : "";
        if (input && !submittedValue) {
            updateControls();
            return;
        }

        pending = true;
        updateControls();

        try {
            await onSubmit(submittedValue);
            closeDialog();
        } catch (error) {
            pending = false;
            updateControls();
            showErrorToast(errorSummary, error, errorDetail);
        }
    };

    if (input) {
        input.addEventListener("input", updateControls);
        input.addEventListener("keydown", (event) => {
            if (event.key !== "Enter") {
                return;
            }
            event.preventDefault();
            if (!submitButton.disabled) {
                void handleSubmit();
            }
        });
    }

    const dialogChildren = [
        createElement("h3", {
            className: "mutiny-token-dialog-title",
            textContent: title,
        }),
        createElement(
            "div",
            { className: "mutiny-token-dialog-copy" },
            descriptionLines.map((line) =>
                createElement("p", {
                    textContent: line,
                }),
            ),
        ),
    ];

    if (input && fieldLabel) {
        dialogChildren.push(
            createElement("label", { className: "mutiny-token-dialog-field" }, [
                createElement("span", {
                    className: "mutiny-token-dialog-label",
                    textContent: fieldLabel,
                }),
                input,
            ]),
        );
    }

    dialogChildren.push(
        createElement("div", { className: "mutiny-token-dialog-actions" }, [
            cancelButton,
            submitButton,
        ]),
    );

    dialog.show(
        createElement(
            "div",
            { className: "mutiny-token-dialog-body" },
            dialogChildren,
        ),
    );
    document.body.appendChild(dialog.element);
    dialog.element.style.zIndex = "2147483647";

    updateControls();

    if (input) {
        window.requestAnimationFrame(() => {
            input.focus();
            input.select();
        });
    }
}

class MutinySettingsCache {
    constructor() {
        this.snapshot = createDefaultSnapshot();
        this.ready = false;
        this.listeners = new Set();
    }

    subscribe(listener) {
        this.listeners.add(listener);
        return () => {
            this.listeners.delete(listener);
        };
    }

    notify() {
        for (const listener of this.listeners) {
            listener(this.snapshot);
        }
    }

    getSnapshot() {
        return this.snapshot;
    }

    isReady() {
        return this.ready;
    }

    applySettingsStatus(payload) {
        const normalized = normalizeSettingsStatus(payload);
        const currentDiskUsage = this.snapshot.cache?.diskUsage;
        this.snapshot = {
            ...normalized,
            cache: {
                ...normalized.cache,
                diskUsage: currentDiskUsage || normalized.cache.diskUsage,
            },
        };
        this.ready = true;
        this.notify();
    }

    finishInitialLoad() {
        this.ready = true;
        this.notify();
    }

    setTokenConfigured(tokenConfigured) {
        this.snapshot = {
            ...this.snapshot,
            discord: {
                ...this.snapshot.discord,
                tokenConfigured,
            },
        };
        this.ready = true;
        this.notify();
    }

    applyCacheStatus(payload) {
        this.snapshot = {
            ...this.snapshot,
            cache: {
                ...this.snapshot.cache,
                diskUsage: {
                    usedBytes: payload.used_bytes ?? 0,
                    maxBytes:
                        payload.max_bytes ??
                        this.snapshot.cache.diskUsage.maxBytes,
                    percentUsed: payload.percent_used ?? 0,
                },
            },
        };
        this.ready = true;
        this.notify();
    }
}

class MutinySettingsApi {
    async loadSettings() {
        return fetchJson(`${API_ROOT}/settings`);
    }

    async loadCacheStatus() {
        return fetchJson(`${API_ROOT}/cache/status`);
    }

    async savePartialSettings(payload) {
        return fetchJson(`${API_ROOT}/settings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
    }

    async saveToken(token) {
        return fetchJson(`${API_ROOT}/token`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token }),
        });
    }

    async clearToken() {
        return fetchJson(`${API_ROOT}/token`, {
            method: "DELETE",
        });
    }
}

async function refreshCacheStatus(cache, apiClient) {
    try {
        const payload = await apiClient.loadCacheStatus();
        cache.applyCacheStatus(payload);
    } catch {
        // Keep cache-usage polling silent so settings remains usable even if the
        // status probe cannot read the SQLite store.
    }
}

function commitInputOnEnter(input) {
    input.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") {
            return;
        }
        event.preventDefault();
        input.blur();
    });
}

function createSectionDescriptionElement(sectionKey, noteParts = []) {
    const note = createElement("div", {
        className: "mutiny-settings-section-note",
        "data-mutiny-section-note": sectionKey,
    });

    for (const part of noteParts) {
        if (typeof part === "string") {
            note.appendChild(document.createTextNode(part));
            continue;
        }

        if (part.type === "strong") {
            note.appendChild(
                createElement("strong", {
                    textContent: part.text,
                }),
            );
            continue;
        }

        note.appendChild(
            createElement("a", {
                href: part.href,
                target: "_blank",
                rel: "noopener noreferrer",
                textContent: part.label,
            }),
        );
    }

    return note;
}

function createInlineNoteElement(noteText, { muted = false } = {}) {
    return createElement("div", {
        className: "mutiny-settings-note",
        "data-muted": muted ? "true" : "false",
        textContent: noteText,
    });
}

function stretchDisplayRow(
    rootElement,
    layout,
    { pullUp = false, centerContent = false } = {},
) {
    layout.registerDisplayRow(rootElement, { pullUp, centerContent });
}

const SECTION_DESCRIPTION_DEFINITIONS = {
    discord: [
        "Configure the Discord server and channel Mutiny uses, and manage your Discord token securely. To find Guild ID and Channel ID, enable Discord Developer Mode and follow ",
        {
            href: DISCORD_ID_GUIDE_URL,
            label: "this setup guide",
        },
        ".",
        " ",
        {
            type: "strong",
            text: "Mutiny does not explain how to obtain your Discord token; you must determine that yourself.",
        },
    ],
    cache: [
        "Mutiny uses its cache to recognize previously seen Midjourney images and videos. It stores recognition data such as hashes and action context, not the media itself, so features that depend on identifying prior outputs and their valid follow-up actions continue to work.",
    ],
};

const SUPPORT_FOOTER_LINKS = [
    {
        href: "https://artificialsweetener.ai",
        label: "Website",
        brand: "website",
    },
    {
        href: "https://github.com/Artificial-Sweetener/ComfyUI-Mutiny/",
        label: "GitHub",
        brand: "github",
    },
    {
        href: "https://ko-fi.com/artificial_sweetener",
        label: "Ko-fi",
        brand: "kofi",
    },
    {
        href: "https://www.patreon.com/ArtificialSweetener",
        label: "Patreon",
        brand: "patreon",
    },
];

function attachSectionDescription(sectionKey, anchorId) {
    const anchor = document.getElementById(anchorId);
    if (!anchor) {
        return;
    }

    const group = anchor.closest(".setting-group");
    if (
        !group ||
        group.querySelector(`[data-mutiny-section-note="${sectionKey}"]`)
    ) {
        return;
    }

    const heading = group.querySelector("h3");
    if (!heading) {
        return;
    }

    heading.insertAdjacentElement(
        "afterend",
        createSectionDescriptionElement(
            sectionKey,
            SECTION_DESCRIPTION_DEFINITIONS[sectionKey],
        ),
    );
}

function installSectionDescriptions() {
    const sync = () => {
        attachSectionDescription("discord", "Mutiny.Discord.GuildId");
        attachSectionDescription("cache", "Mutiny.Cache.ArtifactCacheRamMaxMb");
    };

    sync();

    observeBodyMutations(sync);
}

function createSupportFooterElement() {
    const footer = createElement("div", {
        className: "mutiny-settings-footer",
        "data-mutiny-footer": "support",
    });

    footer.appendChild(
        createElement("div", {
            className: "mutiny-settings-footer-copy",
            textContent:
                "Mutiny takes real time and money to build and maintain. If it helps you, support keeps it alive.",
        }),
    );

    footer.appendChild(
        createElement(
            "div",
            { className: "mutiny-settings-footer-links" },
            SUPPORT_FOOTER_LINKS.map((link) =>
                createElement(
                    "a",
                    {
                        className: "mutiny-settings-footer-button",
                        href: link.href,
                        target: "_blank",
                        rel: "noopener noreferrer",
                        "data-brand": link.brand,
                    },
                    [
                        createSupportFooterIcon(link.brand),
                        createElement("span", {
                            textContent: link.label,
                        }),
                    ],
                ),
            ),
        ),
    );

    return footer;
}

function createSupportFooterIcon(brand) {
    const svg = createSvgElement("svg", {
        className: "mutiny-settings-footer-button-icon",
        viewBox: "0 0 24 24",
        "aria-hidden": "true",
        fill: "none",
        stroke: "currentColor",
        "stroke-width": "2",
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
    });

    const pathMap = {
        website: [
            ["circle", { cx: "12", cy: "12", r: "9" }],
            ["path", { d: "M3 12h18" }],
            ["path", { d: "M12 3a14 14 0 0 1 0 18" }],
            ["path", { d: "M12 3a14 14 0 0 0 0 18" }],
        ],
        github: [
            ["path", { d: "M9 19c-4.5 1.5-4.5-2.5-6.5-3" }],
            [
                "path",
                {
                    d: "M14.5 21v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 18.5 3.77 5.07 5.07 0 0 0 18.41 1S17.27.65 14.5 2.48a13.38 13.38 0 0 0-5 0C6.73.65 5.59 1 5.59 1a5.07 5.07 0 0 0-.09 2.77A5.44 5.44 0 0 0 4 7.52c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9.5 17.13V21",
                },
            ],
        ],
        kofi: [
            ["path", { d: "M5 9h10a3 3 0 0 1 0 6h-1" }],
            ["path", { d: "M5 9v4a5 5 0 0 0 5 5h3a5 5 0 0 0 5-5V9" }],
            ["path", { d: "M8 5c0 2 2 2 2 4" }],
            ["path", { d: "M12 5c0 2 2 2 2 4" }],
        ],
        patreon: [
            ["circle", { cx: "8", cy: "12", r: "4" }],
            ["path", { d: "M16 5v14" }],
        ],
    };

    for (const [tagName, attrs] of pathMap[brand] || []) {
        svg.appendChild(createSvgElement(tagName, attrs));
    }

    return svg;
}

/**
 * Return true when the Mutiny settings anchor belongs to the active visible settings page.
 */
function isVisibleMutinySettingsAnchor(anchor) {
    return (
        anchor?.nodeType === Node.ELEMENT_NODE &&
        anchor.isConnected &&
        anchor.getClientRects().length > 0 &&
        !anchor.closest('[hidden],[aria-hidden="true"],[inert]')
    );
}

/**
 * Locate the container that should own the docked Mutiny support footer.
 */
function findSupportFooterHost(mutinyAnchor) {
    const dialogMain = mutinyAnchor.closest("main");
    const scrollRegion = mutinyAnchor.closest(".overflow-y-auto");
    if (
        dialogMain?.nodeType === Node.ELEMENT_NODE &&
        scrollRegion?.nodeType === Node.ELEMENT_NODE &&
        scrollRegion.parentElement === dialogMain
    ) {
        return dialogMain;
    }

    const legacyPanelRoot = mutinyAnchor.closest('[role="tabpanel"]');
    if (legacyPanelRoot?.nodeType === Node.ELEMENT_NODE) {
        return legacyPanelRoot;
    }

    return null;
}

/**
 * Coalesce body mutation bursts into a single sync pass per animation frame.
 */
function observeBodyMutations(sync) {
    let syncScheduled = false;
    const scheduleSync = () => {
        if (syncScheduled) {
            return;
        }

        syncScheduled = true;
        window.requestAnimationFrame(() => {
            syncScheduled = false;
            sync();
        });
    };

    const observer = new window.MutationObserver((mutations) => {
        if (
            !mutations.some(
                (mutation) =>
                    mutation.addedNodes.length > 0 ||
                    mutation.removedNodes.length > 0,
            )
        ) {
            return;
        }

        scheduleSync();
    });
    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
}

/**
 * Remove every injected Mutiny support footer from the current document.
 */
function removeSupportFooters() {
    document
        .querySelectorAll('[data-mutiny-footer="support"]')
        .forEach((footer) => footer.remove());
}

function installSupportFooter() {
    const sync = () => {
        const mutinyAnchor = document.getElementById(
            "Mutiny.Runtime.TaskTimeoutMinutes",
        );
        if (!isVisibleMutinySettingsAnchor(mutinyAnchor)) {
            removeSupportFooters();
            return;
        }

        const footerHost = findSupportFooterHost(mutinyAnchor);
        if (!footerHost) {
            removeSupportFooters();
            return;
        }

        document
            .querySelectorAll('[data-mutiny-footer="support"]')
            .forEach((footer) => {
                if (footer.parentElement !== footerHost) {
                    footer.remove();
                }
            });

        let footer = footerHost.querySelector('[data-mutiny-footer="support"]');
        if (!footer) {
            footer = createSupportFooterElement();
            footerHost.appendChild(footer);
        }
    };

    sync();

    observeBodyMutations(sync);
}

function createDiskCacheUsageMeter(cache) {
    const label = createElement("div", {
        className: "mutiny-settings-help",
    });
    const fill = createElement("div", {
        className: "mutiny-settings-meter-fill",
    });
    const meter = createElement("div", { className: "mutiny-settings-meter" }, [
        createElement("div", { className: "mutiny-settings-meter-bar" }, [
            fill,
        ]),
        label,
    ]);

    const sync = () => {
        const usage = cache.getSnapshot().cache.diskUsage;
        fill.style.width = `${usage.percentUsed}%`;
        label.textContent =
            `Using ${formatMegabytes(usage.usedBytes)} of ` +
            `${formatMegabytes(usage.maxBytes)} (${usage.percentUsed}% full)`;
    };

    cache.subscribe(sync);
    sync();
    return meter;
}

function createDisplayNoteRenderer({ definition, layout }) {
    const note = createInlineNoteElement(definition.noteText, {
        muted: Boolean(definition.muted),
    });
    stretchDisplayRow(note, layout, { pullUp: true });
    return note;
}

function createDiskUsageRenderer({ cache, layout }) {
    const meter = createDiskCacheUsageMeter(cache);
    meter.dataset.display = "wide";
    stretchDisplayRow(meter, layout, { centerContent: true });
    return meter;
}

function createTextSettingRenderer({ cache, apiClient, definition, layout }) {
    const inputAttributes = definition.maskedWithReveal
        ? buildMaskedTextInputAttributes({
              className: "mutiny-settings-input p-inputtext p-component",
              placeholder: definition.placeholder,
          })
        : {
              className: "mutiny-settings-input p-inputtext p-component",
              placeholder: definition.placeholder,
              type: definition.inputType || "text",
          };
    const input = createElement("input", inputAttributes);
    const wrapperChildren = [input];
    let revealButton = null;
    let revealed = false;

    if (definition.maskedWithReveal) {
        revealButton = createButton("Show", {
            kind: "secondary",
            onClick: () => {
                revealed = !revealed;
                sync();
                input.focus();
            },
        });
        revealButton.dataset.revealToggle = "true";
        wrapperChildren.push(revealButton);
    }

    const wrapper = createElement(
        "div",
        {
            className: "mutiny-settings-field",
            "data-maskable": definition.maskedWithReveal ? "true" : "false",
        },
        wrapperChildren,
    );
    const stackChildren = [wrapper];
    if (definition.helpText) {
        stackChildren.push(
            createElement("div", {
                className: "mutiny-settings-help",
                textContent: definition.helpText,
            }),
        );
    }
    if (definition.createSupplementary) {
        stackChildren.push(
            definition.createSupplementary({
                cache,
                apiClient,
            }),
        );
    }
    const rendered =
        stackChildren.length === 1
            ? wrapper
            : createElement(
                  "div",
                  { className: "mutiny-settings-control-stack" },
                  stackChildren,
              );

    if (definition.section === "discord") {
        layout.registerDiscordRow(wrapper);
    }

    if (definition.min !== undefined) {
        input.min = String(definition.min);
    }
    if (definition.step !== undefined) {
        input.step = String(definition.step);
    }

    let pending = false;
    let lastCommittedValue = definition.formatValue(
        definition.readValue(cache.getSnapshot()),
    );
    let draftValue = lastCommittedValue;

    const sync = () => {
        const nextCommittedValue = definition.formatValue(
            definition.readValue(cache.getSnapshot()),
        );
        const shouldRefreshDraft =
            pending ||
            draftValue === lastCommittedValue ||
            document.activeElement !== input;

        lastCommittedValue = nextCommittedValue;
        if (shouldRefreshDraft) {
            draftValue = nextCommittedValue;
        }

        if (input.value !== draftValue) {
            input.value = draftValue;
        }

        input.disabled = pending || !cache.isReady();
        if (definition.maskedWithReveal && revealButton) {
            input.setAttribute("data-masked", revealed ? "false" : "true");
            revealButton.disabled = pending || !cache.isReady();
            setButtonLabel(revealButton, revealed ? "Hide" : "Show");
        }
        wrapper.dataset.pending = pending ? "true" : "false";
    };

    const revertDraft = () => {
        draftValue = lastCommittedValue;
        sync();
    };

    input.addEventListener("input", (event) => {
        draftValue = event.target.value;
    });

    input.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }
        event.preventDefault();
        revertDraft();
        input.blur();
    });

    input.addEventListener("change", async (event) => {
        const nextDraftValue = event.target.value;
        draftValue = nextDraftValue;

        if (nextDraftValue === lastCommittedValue) {
            sync();
            return;
        }

        let parsedValue;
        try {
            parsedValue = definition.parseValue(nextDraftValue);
        } catch (error) {
            revertDraft();
            showErrorToast(
                `Failed to save ${definition.name}.`,
                error,
                `Unable to validate ${definition.name}.`,
            );
            return;
        }

        pending = true;
        sync();

        try {
            const payload = await apiClient.savePartialSettings(
                definition.buildPayload(parsedValue),
            );
            cache.applySettingsStatus(payload);
            void refreshCacheStatus(cache, apiClient);
        } catch (error) {
            revertDraft();
            showErrorToast(
                `Failed to save ${definition.name}.`,
                error,
                `Unable to save ${definition.name}.`,
            );
        } finally {
            pending = false;
            sync();
        }
    });

    commitInputOnEnter(input);
    cache.subscribe(sync);
    sync();

    return rendered;
}

function createNumberSettingRenderer({ cache, apiClient, definition, layout }) {
    return createTextSettingRenderer({ cache, apiClient, definition, layout });
}

function parseWholeNumberSetting(value, { name, minimum }) {
    const trimmedValue = String(value).trim();
    if (!trimmedValue) {
        throw new Error(`${name} must be a whole number.`);
    }

    const parsedValue = Number.parseInt(trimmedValue, 10);
    if (!Number.isInteger(parsedValue)) {
        throw new Error(`${name} must be a whole number.`);
    }
    if (parsedValue < minimum) {
        throw new Error(`${name} must be greater than or equal to ${minimum}.`);
    }
    return parsedValue;
}

function createTokenSettingRenderer({ cache, apiClient, layout }) {
    const wrapper = createElement("div", {
        className: "mutiny-settings-token-row",
    });

    let pending = false;
    let dialogOpen = false;

    layout.registerDiscordRow(wrapper);

    const setPending = (nextPending) => {
        pending = nextPending;
        render();
    };

    const storeToken = async ({ token, replacing }) => {
        setPending(true);
        try {
            const payload = await apiClient.saveToken(token);
            cache.setTokenConfigured(Boolean(payload.token_configured));
            showSuccessToast(
                replacing ? "Discord token replaced." : "Discord token stored.",
                "The Discord token was stored in your system credential store.",
            );
        } finally {
            setPending(false);
        }
    };

    const clearToken = async () => {
        setPending(true);
        try {
            const payload = await apiClient.clearToken();
            cache.setTokenConfigured(Boolean(payload.token_configured));
            showSuccessToast(
                "Discord token cleared.",
                "The stored Discord token was removed from your system credential store.",
            );
        } finally {
            setPending(false);
        }
    };

    const openTokenDialog = (mode) => {
        dialogOpen = true;
        render();

        openMutinyDialog({
            ...TOKEN_DIALOG_CONTENT[mode],
            onSubmit:
                mode === "clear"
                    ? async () => clearToken()
                    : async (token) =>
                          storeToken({
                              token,
                              replacing: mode === "replace",
                          }),
            onClose: () => {
                dialogOpen = false;
                render();
            },
        });
    };

    const render = () => {
        const tokenConfigured =
            cache.getSnapshot().discord.tokenConfigured && cache.isReady();
        const controlsDisabled = pending || dialogOpen || !cache.isReady();

        wrapper.replaceChildren();
        wrapper.dataset.pending = pending ? "true" : "false";

        if (!tokenConfigured) {
            const addButton = createButton("Add Discord Token", {
                onClick: () => {
                    openTokenDialog("add");
                },
            });
            addButton.dataset.tokenPrimary = "true";
            addButton.disabled = controlsDisabled;
            wrapper.appendChild(addButton);
            layout.scheduleDiscordWidthSync();
            return;
        }

        const replaceButton = createButton("Replace Discord Token", {
            onClick: () => {
                openTokenDialog("replace");
            },
        });
        replaceButton.dataset.tokenPrimary = "true";
        const clearButton = createButton("Clear", {
            kind: "secondary",
            onClick: () => {
                openTokenDialog("clear");
            },
        });

        replaceButton.disabled = controlsDisabled;
        clearButton.disabled = controlsDisabled;

        wrapper.appendChild(replaceButton);
        wrapper.appendChild(clearButton);
        layout.scheduleDiscordWidthSync();
    };

    cache.subscribe(render);
    render();

    return wrapper;
}

const TEXT_ROW_DEFINITIONS = [
    {
        id: "Mutiny.Discord.GuildId",
        name: "Guild ID",
        section: "discord",
        tooltip: "Required Discord server identifier for job submission.",
        sortOrder: 400,
        maskedWithReveal: true,
        readValue: (snapshot) => snapshot.discord.guildId,
        formatValue: (value) => String(value || ""),
        parseValue: (value) => value,
        buildPayload: (value) => ({ discord: { guild_id: value } }),
    },
    {
        id: "Mutiny.Discord.ChannelId",
        name: "Channel ID",
        section: "discord",
        tooltip: "Required Discord channel identifier for job submission.",
        sortOrder: 390,
        maskedWithReveal: true,
        readValue: (snapshot) => snapshot.discord.channelId,
        formatValue: (value) => String(value || ""),
        parseValue: (value) => value,
        buildPayload: (value) => ({ discord: { channel_id: value } }),
    },
    {
        id: "Mutiny.Discord.ApiEndpoint",
        name: "API Endpoint",
        section: "discord",
        tooltip: "Override the Discord API base URL when needed.",
        sortOrder: 360,
        readValue: (snapshot) => snapshot.discord.apiEndpoint,
        formatValue: (value) => String(value || ""),
        parseValue: (value) => value,
        buildPayload: (value) => ({ discord: { api_endpoint: value } }),
    },
    {
        id: "Mutiny.Cache.ArtifactCacheRamMaxMb",
        name: "Artifact RAM (MB)",
        inputType: "number",
        min: 1,
        step: 1,
        tooltip: "Maximum RAM budget for Mutiny's artifact recognition cache.",
        sortOrder: 355,
        readValue: (snapshot) => snapshot.cache.artifactCacheRamMaxMb,
        formatValue: (value) => String(value ?? 32),
        parseValue: (value) =>
            parseWholeNumberSetting(value, {
                name: "Artifact Cache RAM (MB)",
                minimum: 1,
            }),
        buildPayload: (value) => ({
            cache: { artifact_cache_ram_max_mb: value },
        }),
    },
    {
        id: "Mutiny.Cache.ArtifactCacheRamHelp",
        name: "\u00A0",
        sortOrder: 354,
        rendererFactory: createDisplayNoteRenderer,
        muted: true,
        noteText:
            "Memory budget for Mutiny's active cache. Lower it to stay lean on RAM; evicted entries can still be reloaded from disk.",
    },
    {
        id: "Mutiny.Cache.DiskCacheMaxMb",
        name: "Artifact Disk (MB)",
        inputType: "number",
        min: 1,
        step: 1,
        tooltip: "Maximum disk budget for Mutiny's persistent artifact cache.",
        sortOrder: 352,
        readValue: (snapshot) => snapshot.cache.diskCacheMaxMb,
        formatValue: (value) => String(value ?? 256),
        parseValue: (value) =>
            parseWholeNumberSetting(value, {
                name: "Artifact Cache Disk (MB)",
                minimum: 1,
            }),
        buildPayload: (value) => ({
            cache: { disk_cache_max_mb: value },
        }),
    },
    {
        id: "Mutiny.Cache.DiskCacheHelp",
        name: "\u00A0",
        sortOrder: 351,
        rendererFactory: createDisplayNoteRenderer,
        muted: true,
        noteText:
            "Disk budget for persistent recognition data. When full, older entries are forgotten and Mutiny can lose context for older Midjourney outputs. Increase it if long-term recognition matters; 256 MB is already generous.",
    },
    {
        id: "Mutiny.Cache.DiskCacheUsage",
        name: "\u00A0",
        sortOrder: 350.5,
        rendererFactory: createDiskUsageRenderer,
    },
    {
        id: "Mutiny.Runtime.TaskTimeoutMinutes",
        name: "Task Timeout Minutes",
        inputType: "number",
        min: 1,
        step: 1,
        tooltip: "Maximum runtime wait before a Mutiny job times out.",
        sortOrder: 350,
        readValue: (snapshot) => snapshot.runtime.taskTimeoutMinutes,
        formatValue: (value) => String(value ?? 5),
        parseValue: (value) =>
            parseWholeNumberSetting(value, {
                name: "Task Timeout Minutes",
                minimum: 1,
            }),
        buildPayload: (value) => ({
            engine: { execution: { task_timeout_minutes: value } },
        }),
    },
];

const TOKEN_ROW_DEFINITION = {
    id: "Mutiny.Discord.DiscordToken",
    name: "Discord Token",
    sortOrder: 385,
    tooltip:
        "Save, replace, or clear the Discord token without exposing it in plugin files.",
};

function registerSetting({ id, name, render, sortOrder, tooltip }) {
    app.ui.settings.addSetting({
        defaultValue: "",
        id,
        name,
        sortOrder,
        tooltip,
        type() {
            return render();
        },
    });
}

function registerMutinySettings({ cache, apiClient, layout }) {
    const renderedRows = new Map();
    const getOrCreateRow = (id, factory) => {
        if (!renderedRows.has(id)) {
            renderedRows.set(id, factory());
        }
        return renderedRows.get(id);
    };

    for (const definition of TEXT_ROW_DEFINITIONS) {
        const createRenderer =
            definition.rendererFactory ||
            (definition.inputType === "number"
                ? createNumberSettingRenderer
                : createTextSettingRenderer);
        registerSetting({
            id: definition.id,
            name: definition.name,
            sortOrder: definition.sortOrder,
            tooltip: definition.tooltip,
            render: () =>
                getOrCreateRow(definition.id, () =>
                    createRenderer({
                        cache,
                        apiClient,
                        definition,
                        layout,
                    }),
                ),
        });
    }

    registerSetting({
        id: TOKEN_ROW_DEFINITION.id,
        name: TOKEN_ROW_DEFINITION.name,
        sortOrder: TOKEN_ROW_DEFINITION.sortOrder,
        tooltip: TOKEN_ROW_DEFINITION.tooltip,
        render: () =>
            getOrCreateRow(TOKEN_ROW_DEFINITION.id, () =>
                createTokenSettingRenderer({
                    cache,
                    apiClient,
                    layout,
                }),
            ),
    });
}

async function initializeSettings(cache, apiClient) {
    try {
        const payload = await apiClient.loadSettings();
        cache.applySettingsStatus(payload);
        await refreshCacheStatus(cache, apiClient);
    } catch (error) {
        cache.finishInitialLoad();
        showErrorToast(
            "Failed to load Mutiny settings.",
            error,
            "Unable to load Mutiny settings.",
        );
    }
}

function installMutinySetupFailureDialog(apiClient) {
    let activeDialog = null;
    let activePromptId = null;

    api.addEventListener("execution_error", async ({ detail }) => {
        const errorMessage = detail?.exception_message || "";
        if (!isMutinyMissingSetupMessage(errorMessage)) {
            return;
        }

        if (activePromptId === detail?.prompt_id && activeDialog) {
            return;
        }

        let missingState;
        try {
            missingState = await readMutinyMissingSetupState(apiClient);
        } catch {
            missingState =
                inferMutinyMissingSetupStateFromMessage(errorMessage);
        }

        if (activeDialog) {
            activeDialog.close();
            activeDialog.element.remove();
        }

        activePromptId = detail?.prompt_id || null;
        activeDialog = openMutinySetupRequiredDialog(missingState, {
            onClose: () => {
                activeDialog = null;
                activePromptId = null;
            },
        });
    });
}

app.registerExtension({
    name: EXTENSION_NAME,
    async setup() {
        installStyleSheet();

        const cache = new MutinySettingsCache();
        const apiClient = new MutinySettingsApi();
        const layout = new MutinySettingsLayoutCoordinator();

        registerMutinySettings({ cache, apiClient, layout });
        installSectionDescriptions();
        installSupportFooter();
        installMutinySetupFailureDialog(apiClient);
        void initializeSettings(cache, apiClient);
        window.setInterval(() => {
            void refreshCacheStatus(cache, apiClient);
        }, 15000);
    },
});
