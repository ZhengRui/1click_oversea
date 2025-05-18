/**
 * simHover.js - Utility for simulating hover events on elements
 *
 * This script detects and simulates hover events on specified elements,
 * useful for expanding content that only displays on hover.
 */

(() => {
  const simulateHover = (element) => {
    const mouseenterEvent = new MouseEvent("mouseenter", {
      view: window,
      bubbles: true,
      cancelable: true,
    });

    const mouseoverEvent = new MouseEvent("mouseover", {
      view: window,
      bubbles: true,
      cancelable: true,
    });

    element.dispatchEvent(mouseenterEvent);
    element.dispatchEvent(mouseoverEvent);
  };

  const expandHoverElements = (selectors) => {
    console.log("Attempting to hover on elements:", selectors);
    let expandedCount = 0;

    // Process hover elements
    selectors.forEach((selector) => {
      try {
        const elements = document.querySelectorAll(selector);
        if (elements.length > 0) {
          console.log(
            `Found ${elements.length} expandable element(s) for: ${selector}`
          );
          elements.forEach((el) => {
            simulateHover(el);
            expandedCount++;
          });
        } else {
          console.warn(`No expandable elements found for: ${selector}`);
        }
      } catch (e) {
        console.error(`Error hovering on ${selector}:`, e);
      }
    });

    console.log(`Expanded ${expandedCount} elements via hover simulation`);

    // Return promise to allow time for hover effects to complete
    return new Promise((resolve) => {
      setTimeout(
        () => resolve(`Expanded ${expandedCount} hover elements`),
        1500
      );
    });
  };

  // Make the function available globally
  window.expandHoverElements = expandHoverElements;

  // Return the function as well
  return expandHoverElements;
})();
