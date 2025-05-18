/**
 * highlight.js - Utility for visually highlighting DOM elements
 *
 * This script applies visual styling to specified elements to make them
 * stand out on the page for inspection and debugging.
 */

(() => {
  const highlightElements = (selectors) => {
    console.log("Attempting to highlight elements for selectors:", selectors);
    let highlightedCount = 0;

    selectors.forEach((selector) => {
      try {
        const elements = document.querySelectorAll(selector);
        if (elements.length > 0) {
          console.log(
            `Found ${elements.length} element(s) for selector: ${selector}`
          );
          elements.forEach((el) => {
            el.style.backgroundColor = "rgba(255, 255, 0, 0.7)";
            el.style.border = "2px solid red";
            el.style.outline = "1px dashed blue";
            el.style.boxShadow = "0 0 5px 2px orange";
            el.setAttribute("data-highlighted-by-script", selector);
            highlightedCount++;
          });
        } else {
          console.warn(`No elements found for selector: ${selector}`);
        }
      } catch (e) {
        console.error(`Error applying selector ${selector}:`, e);
      }
    });

    const confirmMsg = `Highlighted ${highlightedCount} elements using ${selectors.length} selectors.`;
    console.log(confirmMsg + " Check console for details.");
    return confirmMsg;
  };

  // Make the function available globally
  window.highlightElements = highlightElements;

  // Return the function as well
  return highlightElements;
})();
