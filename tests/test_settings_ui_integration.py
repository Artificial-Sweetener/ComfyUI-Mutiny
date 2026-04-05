"""Guard the native ComfyUI settings integration used by the Mutiny frontend."""

from __future__ import annotations

from pathlib import Path


def test_settings_ui_uses_native_grouped_mutiny_rows():
    """Keep the Mutiny settings UI as grouped native rows with modal token actions."""
    settings_script = (
        Path(__file__).resolve().parents[1] / "web" / "js" / "mutiny-settings.js"
    ).read_text(encoding="utf-8")

    for setting_id in (
        'id: "Mutiny.Discord.GuildId"',
        'id: "Mutiny.Discord.ChannelId"',
        'id: "Mutiny.Discord.DiscordToken"',
        'id: "Mutiny.Discord.UserAgent"',
        'id: "Mutiny.Discord.ApiEndpoint"',
        'id: "Mutiny.Cache.ArtifactCacheRamMaxMb"',
        'id: "Mutiny.Cache.ArtifactCacheRamHelp"',
        'id: "Mutiny.Cache.DiskCacheMaxMb"',
        'id: "Mutiny.Cache.DiskCacheHelp"',
        'id: "Mutiny.Cache.DiskCacheUsage"',
        'id: "Mutiny.Runtime.TaskTimeoutMinutes"',
    ):
        assert setting_id in settings_script

    assert "app.ui.settings.addSetting" in settings_script
    assert "const { ComfyDialog } = window.comfyAPI.ui;" in settings_script
    assert "category:" not in settings_script
    assert (
        'className: "mutiny-settings-input p-inputtext p-component"' in settings_script
    )
    assert "--mutiny-settings-inline-gap: 0.5rem;" in settings_script
    assert "--mutiny-settings-explainer-width: 80%;" in settings_script
    assert 'revealButton.dataset.revealToggle = "true";' in settings_script
    assert "measureNaturalButtonWidth" in settings_script
    assert "MutinySettingsLayoutCoordinator" in settings_script
    assert "this.displayRows = new Map();" in settings_script
    assert "registerDisplayRow(rootElement, options = {})" in settings_script
    assert "this.syncDisplayRows();" in settings_script
    assert "applyDisplayRowLayout(" in settings_script
    assert "scheduleDiscordWidthSync" in settings_script
    assert 'section: "discord"' in settings_script
    assert "parseWholeNumberSetting" in settings_script
    assert "createSectionDescriptionElement" in settings_script
    assert "SECTION_DESCRIPTION_DEFINITIONS" in settings_script
    assert "installSectionDescriptions" in settings_script
    assert "SUPPORT_FOOTER_LINKS" in settings_script
    assert "installSupportFooter" in settings_script
    assert "createSupportFooterElement" in settings_script
    assert "createSupportFooterIcon" in settings_script
    assert "createSvgElement" in settings_script
    assert "document.createElementNS(" in settings_script
    assert 'createElement("strong"' in settings_script
    assert 'type: "strong"' in settings_script
    assert 'element.setAttribute("class", value);' in settings_script
    assert "window.MutationObserver" in settings_script
    assert "window.requestAnimationFrame" in settings_script
    assert "data-mutiny-section-note" in settings_script
    assert 'data-mutiny-footer="support"' in settings_script
    assert (
        'attachSectionDescription("discord", "Mutiny.Discord.GuildId")'
        in settings_script
    )
    assert (
        'attachSectionDescription("cache", "Mutiny.Cache.ArtifactCacheRamMaxMb")'
        in settings_script
    )
    assert "createDiskCacheUsageMeter" in settings_script
    assert "createDisplayNoteRenderer" in settings_script
    assert "createDiskUsageRenderer" in settings_script
    assert "stretchDisplayRow" in settings_script
    assert (
        "layout.registerDisplayRow(rootElement, { pullUp, centerContent });"
        in settings_script
    )
    assert '.mutiny-settings-meter[data-display="wide"]' in settings_script
    assert "width: min(55%, 36rem);" in settings_script
    assert "min-width: 20rem;" in settings_script
    assert 'meter.dataset.display = "wide";' in settings_script
    assert "centerContent = false" in settings_script
    assert (
        'row.style.justifyContent = centerContent ? "center" : "";' in settings_script
    )
    assert 'formInput.style.margin = centerContent ? "0 auto" : "0";' in settings_script
    assert "formInput.style.justifyContent" in settings_script
    assert '? "center"' in settings_script
    assert ': "flex-start";' in settings_script
    assert 'row.style.marginTop = pullUp ? "-0.5rem" : "";' in settings_script
    assert 'formLabel.style.display = "none";' in settings_script
    assert 'formInput.style.flex = "1 1 100%";' in settings_script
    assert 'name: "\\u00A0"' in settings_script
    assert "loadCacheStatus()" in settings_script
    assert "window.setInterval(() => {" in settings_script
    assert 'addButton.dataset.tokenPrimary = "true";' in settings_script
    assert 'replaceButton.dataset.tokenPrimary = "true";' in settings_script
    assert "flex: 1 1 auto;" in settings_script
    assert "-webkit-text-security: disc;" in settings_script
    assert "mutiny-settings-note" in settings_script
    assert "mutiny-settings-section-note" in settings_script
    assert "mutiny-settings-help" in settings_script
    assert "inline-size: var(--mutiny-settings-explainer-width);" in settings_script
    assert "max-inline-size: var(--mutiny-settings-explainer-width);" in settings_script
    assert "overflow-wrap: anywhere;" in settings_script
    assert "mutiny-settings-meter" in settings_script
    assert "mutiny-settings-footer" in settings_script
    assert "mutiny-settings-footer-button" in settings_script
    assert "mutiny-settings-footer-button-icon" in settings_script
    assert "flex: 0 0 auto;" in settings_script
    assert '"data-muted": muted ? "true" : "false"' in settings_script
    assert "maskedWithReveal: true" in settings_script
    assert 'createButton("Show"' in settings_script
    assert 'classNames = ["p-button", "p-component", "p-button-sm"]' in settings_script
    assert "app.extensionManager?.toast?.add" in settings_script
    assert 'createButton("Add Discord Token"' in settings_script
    assert 'createButton("Replace Discord Token"' in settings_script
    assert 'title: "Add Discord Token"' in settings_script
    assert 'title: "Replace Discord Token"' in settings_script
    assert 'title: "Clear Discord Token"' in settings_script
    assert "system credential store" in settings_script
    assert 'autocomplete: "off"' in settings_script
    assert '"data-1p-ignore": "true"' in settings_script
    assert '"data-lpignore": "true"' in settings_script
    assert '"data-bwignore": "true"' in settings_script
    assert 'classList.add("comfy-dialog", "mutiny-token-dialog")' in settings_script
    assert 'classList.add("mutiny-token-dialog-text")' in settings_script
    assert "document.body.appendChild(dialog.element);" in settings_script
    assert 'dialog.element.style.zIndex = "2147483647";' in settings_script
    assert "z-index: 2147483647;" in settings_script
    assert "mutiny-token-dialog-actions" in settings_script
    assert 'label: "this setup guide"' in settings_script
    assert "Mutiny does not explain how to obtain your Discord token" in settings_script
    assert "installMutinySetupFailureDialog" in settings_script
    assert "Mutiny Setup Required" in settings_script
    assert (
        "Add your Guild ID and Channel ID in ComfyUI Settings under Mutiny."
        in settings_script
    )
    assert 'createButton("Open Setup Guide"' in settings_script
    assert "Mutiny needs your Discord guild ID before it can run." in settings_script
    assert "Mutiny needs your Discord channel ID before it can run." in settings_script
    assert "Mutiny needs your Discord token before it can run." in settings_script
    assert "Mutiny does not provide help with token acquisition." in settings_script
    assert '"__BR__"' not in settings_script
    assert "recognize previously seen Midjourney images and videos" in settings_script
    assert "Mutiny takes real time and money to build and maintain." in settings_script
    assert "https://artificialsweetener.ai" in settings_script
    assert "https://github.com/Artificial-Sweetener/ComfyUI-Mutiny/" in settings_script
    assert "https://ko-fi.com/artificial_sweetener" in settings_script
    assert "https://www.patreon.com/ArtificialSweetener" in settings_script
    assert "website: [" in settings_script
    assert "github: [" in settings_script
    assert "kofi: [" in settings_script
    assert "patreon: [" in settings_script
    assert "Memory budget for Mutiny's active cache." in settings_script
    assert "Disk budget for persistent recognition data." in settings_script
    assert 'name: "Artifact RAM (MB)"' in settings_script
    assert 'name: "Artifact Disk (MB)"' in settings_script
    assert "Using ${formatMegabytes(usage.usedBytes)} of " in settings_script

    for removed_text in (
        'id: "Mutiny.Runtime.ApiSecret"',
        'id: "Mutiny.Runtime.ImageBackend"',
        'id: "Mutiny.Runtime.CustomLoader"',
        'id: "Mutiny.Security.DiscordToken"',
        'id: "Mutiny.Runtime.TestConfiguration"',
        'id: "Mutiny.Features.CustomZoom"',
        'id: "Mutiny.Features.Inpaint"',
        'id: "Mutiny.General.Storage"',
        'id: "Mutiny.General.Actions"',
        'id: "Mutiny.General.Status"',
        'id: "Mutiny.Discord.Description"',
        'id: "Mutiny.Cache.Description"',
        "sectionDescriptionParts",
        '"Test Configuration"',
        "Mutiny settings loaded.",
        '"Save Settings"',
        '"Reload"',
        "createInfoControl",
        "createActionsControl",
        "createStatusControl",
        "createToggleSwitch",
        "createToggleSettingRenderer",
        "createActionButtonRenderer",
        "setStatus(",
        "mutiny-settings-status",
        "mutiny-settings-button-row",
        "mutiny-settings-overlay",
        "mutiny-settings-card",
        "mutiny-settings-panel",
        '"p-toggleswitch p-component"',
        'textContent: "Configured"',
        'createButton("Replace Token"',
        'createButton("Save"',
        'placeholder: "Discord token"',
        'type: "password"',
        "features:",
        "apiSecret",
        "imageBackend",
        "customLoader",
        "apiSettings",
        "imageSettings",
        "testConfiguration(",
        "/settings/test",
        "document.body.appendChild(overlay)",
    ):
        assert removed_text not in settings_script

    assert ".querySelectorAll(" in settings_script
    assert "querySelectorAll('[data-mutiny-footer=\"support\"]')" in settings_script
    assert "findSupportFooterHost" in settings_script
    assert "isVisibleMutinySettingsAnchor" in settings_script
    assert "observeBodyMutations" in settings_script
    assert "removeSupportFooters" in settings_script
    assert "anchor.getClientRects().length > 0" in settings_script
    assert (
        "!anchor.closest('[hidden],[aria-hidden=\"true\"],[inert]')" in settings_script
    )
    assert 'const dialogMain = mutinyAnchor.closest("main");' in settings_script
    assert (
        'const scrollRegion = mutinyAnchor.closest(".overflow-y-auto");'
        in settings_script
    )
    assert "scrollRegion.parentElement === dialogMain" in settings_script
    assert (
        "const legacyPanelRoot = mutinyAnchor.closest('[role=\"tabpanel\"]');"
        in settings_script
    )
    assert "Node.ELEMENT_NODE" in settings_script
    assert "legacyPanelRoot?.nodeType === Node.ELEMENT_NODE" in settings_script
    assert "footer.parentElement !== footerHost" in settings_script
    assert "observeBodyMutations(sync);" in settings_script
    assert "if (!isVisibleMutinySettingsAnchor(mutinyAnchor)) {" in settings_script
    assert "removeSupportFooters();" in settings_script
    assert "if (!footerHost) {" in settings_script
