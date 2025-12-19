(function() {
    if (window.statsCustomizerInterval) clearInterval(window.statsCustomizerInterval);
    document.documentElement.dataset.statsCustomizer = "active";

    function applyChanges() {
        const candidateSelectors = [
            "button",
            "label",
            "[role='button']",
            "[role='tab']",
            "[role='radio']"
        ];

        const candidates = Array.from(
            document.querySelectorAll(candidateSelectors.join(","))
        );
        
        let yearBtn = null;
        let allBtn = null;

        const containsNeedle = (text, needles) => {
            if (!text) {
                return false;
            }
            const normalized = text.toLowerCase();
            return needles.some((needle) => normalized.includes(needle));
        };

        for (const el of candidates) {
            const textBits = [
                el.textContent,
                el.getAttribute("aria-label"),
                el.getAttribute("title"),
                el.getAttribute("data-key"),
            ]
                .filter(Boolean)
                .map((s) => s.trim());

            const haystack = textBits.join(" ").trim();
            if (!haystack) {
                continue;
            }

            if (
                !yearBtn &&
                containsNeedle(haystack, [
                    "1 year",
                    "year",
                    "年間",
                    "１年間",
                    "1年間",
                ]) &&
                !containsNeedle(haystack, ["all", "全", "all history", "全期間"])
            ) {
                yearBtn = el;
            }

            if (
                !allBtn &&
                containsNeedle(haystack, [
                    "all",
                    "all time",
                    "all history",
                    "全",
                    "全期間",
                    "全期間",
                    "全歴史",
                ])
            ) {
                allBtn = el;
            }
        }

        if (yearBtn && yearBtn.style.display !== 'none') {
            yearBtn.style.display = 'none';
        }

        if (allBtn) {
            const isActive = allBtn.classList.contains('active') || 
                             (allBtn.querySelector('input') && allBtn.querySelector('input').checked);
            
            if (!isActive) {
                let siblingActive = false;
                if (allBtn.parentElement) {
                    const siblings = allBtn.parentElement.querySelectorAll('button, label');
                    for (const s of siblings) {
                        if (s !== allBtn && s !== yearBtn) {
                             if (s.classList.contains('active') || (s.querySelector('input') && s.querySelector('input').checked)) {
                                 siblingActive = true;
                             }
                        }
                    }
                }
                
                // If no sibling (Month) is active, then Year (or nothing) is active. Click All.
                if (!siblingActive) {
                    allBtn.click();
                }
            }

            // Hide the All button once it's enforced; there's no reason to show it alone.
            if (allBtn.style.display !== 'none') {
                allBtn.style.display = 'none';
            }

            // If its container now only has hidden children, hide that too.
            if (allBtn.parentElement) {
                const visibleChildren = Array.from(
                    allBtn.parentElement.querySelectorAll('button, label')
                ).filter((el) => el !== allBtn && el.style.display !== 'none');
                if (visibleChildren.length === 0) {
                    allBtn.parentElement.style.display = 'none';
                }
            }
        }
    }

    // Run frequently
    applyChanges();
    window.statsCustomizerInterval = setInterval(applyChanges, 200);
})();

