# -*- coding: utf-8 -*-

# Review Heatmap Add-on for Anki
#
# Copyright (C) 2016-2022  Aristotelis P. <https//glutanimate.com/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version, with the additions
# listed at the end of the accompanied license file.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# NOTE: This program is subject to certain additional terms pursuant to
# Section 7 of the GNU Affero General Public License.  You should have
# received a copy of these additional terms immediately following the
# terms and conditions of the GNU Affero General Public License which
# accompanied this program.
#
# If not, please request a copy through one of the means of contact
# listed here: <https://glutanimate.com/contact/>.
#
# Any modifications to this file must keep this entire header intact.

"""
Integration with Anki views
"""

from __future__ import annotations

import json
from abc import ABC
from typing import TYPE_CHECKING, Callable, Optional

from anki.hooks import addHook, remHook, wrap
from anki.stats import CollectionStats
from aqt.deckbrowser import DeckBrowser
from aqt.main import AnkiQt
from aqt.overview import Overview
from aqt.stats import DeckStats

from .controller import HeatmapController
from .renderer import HeatmapView

if TYPE_CHECKING:
    from aqt.deckbrowser import DeckBrowserContent
    from aqt.overview import OverviewContent  # noqa: F401


class HeatmapInjector(ABC):

    _view: HeatmapView

    def __init__(self, controller: HeatmapController):
        self._controller = controller

    def register(self):
        ...


# Deck Browser (Main view)
######################################################################


class DeckBrowserInjector(HeatmapInjector):

    _view = HeatmapView.deckbrowser

    def register(self):
        from aqt.gui_hooks import deck_browser_will_render_content

        deck_browser_will_render_content.append(self.on_deckbrowser_will_render_content)

    def on_deckbrowser_will_render_content(
        self, deck_browser: DeckBrowser, content: DeckBrowserContent
    ):
        heatmap_html = self._controller.render_for_view(self._view)
        content.stats += heatmap_html


# Overview (Deck view)
######################################################################


class OverviewInjector(HeatmapInjector):

    _view = HeatmapView.overview

    _overview_body: str = """
<center>
<h3>%(deck)s</h3>
%(shareLink)s
%(desc)s
%(table)s
%(stats)s
</center>
<script>$(function () { $("#study").focus(); });</script>
"""

    def register(self):
        from aqt.gui_hooks import overview_did_refresh, overview_will_render_content

        overview_will_render_content.append(self.overview_will_render_content)
        overview_did_refresh.append(self.overview_did_refresh)

    def overview_will_render_content(
        self, overview: Overview, content: OverviewContent
    ):
        if overview.mw.col and overview.mw.col.sched._is_finished():
            return
        heatmap_html = self._controller.render_for_view(
            self._view, current_deck_only=True
        )
        content.table += heatmap_html

    def overview_did_refresh(self, overview: Overview):
        if not overview.mw.col or not overview.mw.col.sched._is_finished():
            return

        heatmap_html = self._controller.render_for_view(
            self._view, current_deck_only=True
        )
        self._inject_finished_heatmap(overview, heatmap_html)

    def _inject_finished_heatmap(self, overview: Overview, heatmap_html: str) -> None:
        container_id = "review-heatmap-finished"
        heatmap_html_json = json.dumps(heatmap_html)
        container_id_json = json.dumps(container_id)

        # Parent-side script (manages container and outer iframe element)
        script_template = """
(() => {
    const heatmapHtml = __FRAME_HTML__;
    const containerId = __CONTAINER_ID__;
    const assetState = window.__reviewHeatmapAssets || (window.__reviewHeatmapAssets = { scripts: {}, styles: {} });
    const inlineStyleId = `${containerId}-inline-style`;

    const ensureContainer = () => {
        const host = document.querySelector("main") || document.body;
        if (!host) {
            return null;
        }

        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement("div");
            container.id = containerId;
            container.style.width = "100%";
            container.style.display = "flex";
            container.style.justifyContent = "center";
            container.style.alignItems = "flex-start";
            container.style.margin = "1.5em 0 1em";
            container.style.padding = "0";
            container.style.overflowX = "visible";
            host.appendChild(container);
        }

        return container;
    };

    const loadStylesheet = (href) => {
        if (!href) {
            return Promise.resolve();
        }
        if (assetState.styles[href]) {
            return assetState.styles[href];
        }
        let link = document.querySelector(`link[href="${href}"]`);
        if (!link) {
            link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = href;
            document.head.appendChild(link);
        }
        const promise = new Promise((resolve) => {
            if (link.sheet) {
                resolve();
                return;
            }
            const finalize = () => resolve();
            link.addEventListener("load", finalize, { once: true });
            link.addEventListener("error", finalize, { once: true });
        });
        assetState.styles[href] = promise;
        return promise;
    };

    const loadScript = (src) => {
        if (!src) {
            return Promise.resolve();
        }
        if (assetState.scripts[src]) {
            return assetState.scripts[src];
        }
        const existing = document.querySelector(`script[src="${src}"]`);
        if (existing && existing.dataset.rhLoaded === "1") {
            return Promise.resolve();
        }
        const script = document.createElement("script");
        script.src = src;
        script.async = false;
        script.dataset.rhPending = "1";
        const promise = new Promise((resolve) => {
            const finalize = () => {
                script.dataset.rhLoaded = "1";
                resolve();
            };
            script.addEventListener("load", finalize, { once: true });
            script.addEventListener("error", finalize, { once: true });
        });
        assetState.scripts[src] = promise;
        document.head.appendChild(script);
        return promise;
    };

    const ensureScopedStyles = () => {
        if (document.getElementById(inlineStyleId)) {
            return;
        }
        const style = document.createElement("style");
        style.id = inlineStyleId;
        style.textContent = `
            #${containerId} {
                width: 100%;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                margin: 1.5em 0 1em;
                padding: 0;
                background: transparent !important;
                background-color: transparent !important;
            }
            #${containerId} .rh-container,
            #${containerId} .heatmap {
                background: transparent !important;
                background-color: transparent !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                margin: 0 auto !important;
            }
            #${containerId} #cal-heatmap,
            #${containerId} .cal-heatmap-container,
            #${containerId} .cal-heatmap-container svg,
            #${containerId} .cal-heatmap-container .graph,
            #${containerId} .cal-heatmap-container .domain-background {
                background: transparent !important;
                background-color: transparent !important;
            }
            #${containerId} .heatmap-controls {
                width: 100% !important;
                max-width: 600px;
                margin-bottom: -0.5em;
            }
            #${containerId} .heatmap-controls .aligncenter {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 1px;
            }
            #${containerId} .heatmap-controls .aligncenter .hm-btn {
                margin-left: 0;
            }
        `;
        document.head.appendChild(style);
    };

    const runInlineScript = (code) => {
        if (!code || !code.trim()) {
            return;
        }
        try {
            new Function(code)();
        } catch (err) {
            console.error("[Review Heatmap] Inline script error:", err);
        }
    };

    const parseMarkup = () => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(heatmapHtml, "text/html");
        const fragment = document.createDocumentFragment();
        // Move all nodes from body into fragment
        while (doc.body.firstChild) {
            fragment.appendChild(doc.body.firstChild);
        }
        // Also move scripts/styles that might end up in head
        while (doc.head.firstChild) {
            fragment.appendChild(doc.head.firstChild);
        }
        const scripts = [];
        fragment.querySelectorAll("script").forEach((script) => {
            scripts.push({
                src: script.src || null,
                text: script.src ? "" : script.textContent || ""
            });
            script.remove();
        });
        const styles = [];
        fragment.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
            if (link.href) {
                styles.push(link.href);
            }
            link.remove();
        });
        return { fragment, scripts, styles };
    };

    const mountHeatmap = async () => {
        const container = ensureContainer();
        if (!container) {
            return;
        }
        if (container.dataset.rhMounting === "1") {
            return;
        }
        container.dataset.rhMounting = "1";

        try {
            ensureScopedStyles();

            const { fragment, scripts, styles } = parseMarkup();
            container.textContent = "";
            container.style.opacity = "0";
            container.style.transition = "opacity 0.2s ease-in";
            container.appendChild(fragment);

            await Promise.all(styles.map((href) => loadStylesheet(href)));

            for (const script of scripts) {
                if (script.src) {
                    await loadScript(script.src);
                } else {
                    runInlineScript(script.text);
                }
            }

            requestAnimationFrame(() => {
                container.style.opacity = "1";
            });
        } catch (err) {
            console.error("[Review Heatmap] mount failed:", err);
        } finally {
            delete container.dataset.rhMounting;
        }
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", mountHeatmap, { once: true });
    } else {
        mountHeatmap();
    }
})();
"""

        script = (
            script_template.replace("__FRAME_HTML__", heatmap_html_json)
            .replace("__CONTAINER_ID__", container_id_json)
        )

        overview.web.eval(script)


# Legacy stats window
######################################################################


class DeckStatsInjector(HeatmapInjector):

    _view = HeatmapView.stats

    def register(self):
        CollectionStats.dueGraph = wrap(
            CollectionStats.dueGraph, self.on_collection_stats_due_graph, "around"
        )
        DeckStats.__init__ = wrap(DeckStats.__init__, self.on_deck_stats_init, "after")
        DeckStats.reject = wrap(DeckStats.reject, self.on_deck_stats_reject, "after")

        import aqt.stats
        if hasattr(aqt.stats, "NewDeckStats"):
            aqt.stats.NewDeckStats.__init__ = wrap(aqt.stats.NewDeckStats.__init__, self.on_deck_stats_init, "after")
            aqt.stats.NewDeckStats.reject = wrap(aqt.stats.NewDeckStats.reject, self.on_deck_stats_reject, "after")

    def on_deck_stats_init(self, deck_stats: DeckStats, mw: AnkiQt):
        deck_stats.form.web.onBridgeCmd = deck_stats._linkHandler  # type: ignore
        # refresh heatmap on options change:
        addHook("reset", deck_stats.refresh)

    def on_deck_stats_reject(self, deck_stats):
        # clean up after ourselves:
        remHook("reset", deck_stats.refresh)

    def on_collection_stats_due_graph(
        self, collection_stats: CollectionStats, _old: Callable
    ) -> str:
        """Wraps dueGraph and adds our heatmap to the stats screen"""
        # self is anki.stats.CollectionStats
        original_html = _old(collection_stats)

        limhist: Optional[int] = None
        limfcst: Optional[int] = None

        if collection_stats.type == 0:
            limhist, limfcst = 31, 31
        elif collection_stats.type == 1:
            limhist, limfcst = 365, 365
        elif collection_stats.type == 2:
            limhist, limfcst = None, None

        heatmap_html = self._controller.render_for_view(
            self._view,
            limhist=limhist,
            limfcst=limfcst,
            current_deck_only=collection_stats.wholeCollection,
        )

        new_html = original_html + heatmap_html

        return new_html


def initialize_views(controller: HeatmapController):
    deck_browser_injector = DeckBrowserInjector(controller)
    deck_browser_injector.register()

    overview_injector = OverviewInjector(controller)
    overview_injector.register()

    deck_stats_injector = DeckStatsInjector(controller)
    deck_stats_injector.register()
