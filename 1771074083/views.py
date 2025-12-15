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

import json
import os
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
    from aqt.overview import OverviewContent


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
        self, deck_browser: DeckBrowser, content: "DeckBrowserContent"
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
        self, overview: Overview, content: "OverviewContent"
    ):
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
        frame_id = "review-heatmap-finished-frame"
        server_url = overview.mw.serverURL()

        # Read shared CSS
        shared_css_path = os.path.join(os.path.dirname(__file__), "web", "heatmap-shared.css")
        shared_css_content = ""
        if os.path.exists(shared_css_path):
            with open(shared_css_path, "r", encoding="utf-8") as f:
                shared_css_content = f.read()

        frame_css = f"""
<style>
/* Reset and Base */
:root {{
    color-scheme: inherit;
}}
html,
body {{
    margin: 0;
    padding: 0;
    background: transparent !important;
    background-color: transparent !important;
    width: 100%;
}}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.4;
    color: inherit;
    /* Center the main content */
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}}

/* Force transparency even when Anki applies night mode classes */
body.night_mode, 
body.nightMode, 
body.night-mode {{
    background: transparent !important;
    background-color: transparent !important;
}}

/* Kill pseudo overlays from other add-ons */
html::before,
html::after,
body::before,
body::after,
.heatmap-frame::before,
.heatmap-frame::after {{
    background: transparent !important;
    background-color: transparent !important;
    box-shadow: none !important;
    filter: none !important;
    content: none !important;
}}

/* Ensure container and heatmap are centered */
.rh-container,
.heatmap {{
    background: transparent !important;
    background-color: transparent !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 auto !important;
}}

#cal-heatmap,
.cal-heatmap-container,
.cal-heatmap-container svg,
.cal-heatmap-container .graph,
.cal-heatmap-container .domain-background {{
    background: transparent !important;
    background-color: transparent !important;
}}

/* 
   Ensure controls use full width so the 33% floats work.
   Otherwise, flex shrinkage causes them to stack.
*/
.heatmap-controls {{
    width: 100% !important;
    max-width: 600px; /* Optional constraint to keep buttons from spreading too far if needed */
}}

/* Injected Shared CSS */
{shared_css_content}
</style>
""".strip()



        # Embedded JS that runs INSIDE the iframe
        transparency_js = """
            (function() {
                const isTransparent = (val) => {
                    if (!val) return false;
                    val = val.trim().toLowerCase();
                    return val === "transparent" || val === "rgba(0, 0, 0, 0)" || val === "rgba(0,0,0,0)";
                };

                const isNone = (val) => {
                    if (!val) return false;
                    val = val.trim().toLowerCase();
                    return val === "none";
                };

                const enforceNodeTransparency = (node) => {
                    if (!node) return;
                    const setTransparent = (prop) => {
                        const val = node.style.getPropertyValue(prop);
                        const prio = node.style.getPropertyPriority(prop);
                        if (!isTransparent(val) || prio !== "important") {
                            node.style.setProperty(prop, "transparent", "important");
                        }
                    };
                    const setNone = (prop) => {
                         const val = node.style.getPropertyValue(prop);
                         const prio = node.style.getPropertyPriority(prop);
                         if (!isNone(val) || prio !== "important") {
                            node.style.setProperty(prop, "none", "important");
                        }
                    };
                    setTransparent("background");
                    setTransparent("background-color");
                    setNone("background-image");
                    setNone("box-shadow");
                };

                const runEnforcement = () => {
                    if (document.documentElement) enforceNodeTransparency(document.documentElement);
                    if (document.body) enforceNodeTransparency(document.body);
                };

                // Safe initialization
                const init = () => {
                    runEnforcement();
                    setInterval(runEnforcement, 50);
                };

                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', init);
                } else {
                    init();
                }
            })();
        """

        frame_html_parts = [
            "<!doctype html>",
            '<html style="background: transparent !important; background-color: transparent !important;">',
            "<head>",
            '<meta charset="utf-8">',
            f'<base href="{server_url}">',
            f'<script>{transparency_js}</script>',
            frame_css,
            "</head>",
            '<body class="heatmap-frame" style="background: transparent !important; background-color: transparent !important;">',
            heatmap_html,
            "</body>",
            "</html>",
        ]

        frame_html = "\n".join(frame_html_parts)
        frame_html_json = json.dumps(frame_html)
        container_id_json = json.dumps(container_id)
        frame_id_json = json.dumps(frame_id)

        # Parent-side script (manages container and outer iframe element)
        script_template = """
(() => {
    const frameHtml = __FRAME_HTML__;
    const containerId = __CONTAINER_ID__;
    const frameId = __FRAME_ID__;

    const mirrorableClass = (cls) => {
        if (!cls) {
            return false;
        }
        return /(night|dark|mode|theme)/i.test(cls);
    };

    const isTransparent = (val) => {
        if (!val) return false;
        val = val.trim().toLowerCase();
        return val === "transparent" || val === "rgba(0, 0, 0, 0)" || val === "rgba(0,0,0,0)";
    };

    const enforceNodeTransparency = (node) => {
        if (!node) return;
        const setTransparent = (prop) => {
            const val = node.style.getPropertyValue(prop);
            const prio = node.style.getPropertyPriority(prop);
            if (!isTransparent(val) || prio !== "important") {
                node.style.setProperty(prop, "transparent", "important");
            }
        };
        setTransparent("background");
        setTransparent("background-color");
    };


    const attachTransparencyInterval = (node, key, onTick) => {
        if (!node) return;
        if (node[key]) clearInterval(node[key]);
        node[key] = setInterval(() => {
            enforceNodeTransparency(node);
            if (onTick) {
                try {
                    onTick();
                } catch (e) { /* ignore */ }
            }
        }, 50); // Faster 50ms interval
        enforceNodeTransparency(node);
        if (onTick) { 
             try { onTick(); } catch(e) {} 
        }
    };

    const ensureContainer = () => {
        const host = document.querySelector("main") || document.body;
        if (!host) {
            return null;
        }

        // Global CSS injection for parent
        if (!document.getElementById("rh-global-transparency")) {
            const style = document.createElement("style");
            style.id = "rh-global-transparency";
            style.innerHTML = `
                #${containerId}, #${frameId} {
                    background: transparent !important;
                    background-color: transparent !important;
                }
            `;
            document.head.appendChild(style);
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
            // Static init
            container.style.setProperty("background", "transparent", "important");
            container.style.setProperty("background-color", "transparent", "important");
            host.appendChild(container);
        }

        attachTransparencyInterval(container, "_rhContainerInterval");
        return container;
    };

    const updateFrameClasses = (frameDoc) => {
        if (!frameDoc || !frameDoc.body) {
            return;
        }
        try {
            frameDoc.body.classList.add("heatmap-frame");

            const parentBody = document.body;
            let wantsDark = false;

            if (parentBody) {
                parentBody.classList.forEach((cls) => {
                    if (mirrorableClass(cls)) {
                        frameDoc.body.classList.add(cls);
                    }
                    if (cls === "night_mode" || cls === "nightMode" || cls === "night-mode") {
                        wantsDark = true;
                    } else if (/dark/i.test(cls) || /night/i.test(cls)) {
                        wantsDark = true;
                    }
                });
            }

            const parentHtml = document.documentElement;
            if (parentHtml && parentHtml.dataset.bsTheme === "dark") {
                wantsDark = true;
            }

            if (wantsDark) {
                frameDoc.body.classList.add("night_mode", "nightMode", "night-mode");
            }

            if (parentHtml && frameDoc.documentElement && parentHtml.dataset.bsTheme) {
                frameDoc.documentElement.dataset.bsTheme = parentHtml.dataset.bsTheme;
            }
        } catch (err) {
            console.error(err);
        }
    };

    const resizeFrame = (frame) => {
        if (!frame || !frame.contentDocument) {
            return;
        }
        try {
            const doc = frame.contentDocument;
            const body = doc.body;
            if (!body) return;

            const extraHeight = 24;
            const height = body.scrollHeight;
            if (height) {
                frame.style.height = height + extraHeight + "px";
            }

            const docElement = doc.documentElement;
            const width = Math.max(
                body.scrollWidth,
                docElement ? docElement.scrollWidth : 0
            );
            if (width) {
                const extraWidth = 8;
                const totalWidth = width + extraWidth;
                frame.style.width = totalWidth + "px";
            }
        } catch(e) { /* ignore */ }
    };

    const insertFrame = () => {
        const container = ensureContainer();
        if (!container) {
            return false;
        }
        
        container.innerHTML = "";

        let frame = document.createElement("iframe");
        frame.id = frameId;
        frame.setAttribute("scrolling", "no");
        frame.setAttribute("frameborder", "0");
        frame.setAttribute("allowtransparency", "true");
        frame.style.display = "block";
        frame.style.border = "0";
        frame.style.margin = "0 auto";
        frame.style.padding = "0";
        frame.style.overflow = "hidden";
        // Static init
        frame.style.setProperty("background", "transparent", "important");
        frame.style.setProperty("background-color", "transparent", "important");
        container.appendChild(frame);

        // HYBRID DEFENSE:
        // 1. Embedded script runs inside.
        // 2. This interval runs outside and forces the frame element AND reaches inside.
        attachTransparencyInterval(frame, "_rhFrameInterval", () => {
            try {
                // Force outer frame (redundant but safe)
                enforceNodeTransparency(frame);
                
                // Reach inside (Parent Watchdog)
                const doc = frame.contentDocument;
                if (doc) {
                    if (doc.documentElement) enforceNodeTransparency(doc.documentElement);
                    if (doc.body) enforceNodeTransparency(doc.body);
                }
            } catch(e) { /* ignore cross-origin/loading errors */ }
        });

        frame.style.height = "0px";
        frame.style.width = "0px";

        frame.onload = () => {
            try {
                if (frame.contentWindow) {
                    try {
                         frame.contentWindow.pycmd = window.pycmd;
                    } catch (e) { /* ignore */ }
                }
                const doc = frame.contentDocument;
                updateFrameClasses(doc);
                resizeFrame(frame);
                setTimeout(() => resizeFrame(frame), 400);
                setTimeout(() => resizeFrame(frame), 1000);

                if (window.ResizeObserver && doc && doc.body) {
                    const resizeObserver = new ResizeObserver(() => resizeFrame(frame));
                    resizeObserver.observe(doc.body);
                    if (doc.documentElement) {
                        resizeObserver.observe(doc.documentElement);
                    }
                    frame._rhResizeObserver = resizeObserver;
                }
            } catch (err) {
                console.error("Heatmap frame load error:", err);
            }
        };

        frame.srcdoc = frameHtml;
        return true;
    };

    if (!insertFrame()) {
        const observer = new MutationObserver(() => {
            if (insertFrame()) {
                observer.disconnect();
            }
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 6000);
    }
})();
"""

        script = (
            script_template.replace("__FRAME_HTML__", frame_html_json)
            .replace("__CONTAINER_ID__", container_id_json)
            .replace("__FRAME_ID__", frame_id_json)
        )

        overview.web.eval(script)


# Legacy stats window
######################################################################

# TODO: NewDeckStats


class DeckStatsInjector(HeatmapInjector):

    _view = HeatmapView.stats

    def register(self):
        CollectionStats.dueGraph = wrap(
            CollectionStats.dueGraph, self.on_collection_stats_due_graph, "around"
        )
        DeckStats.__init__ = wrap(DeckStats.__init__, self.on_deck_stats_init, "after")
        DeckStats.reject = wrap(DeckStats.reject, self.on_deck_stats_reject, "after")

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
