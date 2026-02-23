// Custom cursor and UI enhancements
import { initCursor } from './vendor/cursor.js?v=20240223';

document.addEventListener('DOMContentLoaded', () => {
    // Wait for GSAP to be fully loaded
    const initCursorWhenReady = () => {
        if (!window.gsap) {
            console.warn('GSAP not loaded yet, retrying...');
            setTimeout(initCursorWhenReady, 100);
            return;
        }

        // Initialize just the cursor
        try {
            const { cursor } = initCursor({
                cursor: {
                    // Custom cursor options
                    hoverTargets: 'a, button, .container li',
                    followEase: 0.4,
                    fadeEase: 0.1,
                    hoverScale: 3,
                },
            });

            // Store instances for cleanup if needed
            window.cursorInstances = { cursor };
            console.log('Cursor initialized successfully');
        } catch (err) {
            console.error('Failed to initialize cursor:', err);
        }
    };

    initCursorWhenReady();
});
