// Canonical guide order includes Start. Filename prefixes are stable public URLs,
// not displayed page numbers. Static HTML carries all navigation without JS.
var pages = [
  { file: "index.html", label: "Start" },
  { file: "01-problem.html", label: "Drift" },
  { file: "02-context-tax.html", label: "Context Tax" },
  { file: "03-bottleneck.html", label: "The Shift" },
  { file: "05-modes.html", label: "Modes" },
  { file: "06-four-artifacts.html", label: "Four Artifacts" },
  { file: "07-colocation.html", label: "Co-location" },
  { file: "08-roles.html", label: "Roles & Flow" },
  { file: "10-payoff.html", label: "Adopt" }
];

var currentFile = window.location.pathname.split("/").pop() || "index.html";
var currentIndex = pages.findIndex(function (page) { return page.file === currentFile; });

// Progressive enhancement only: no rebuilding, scrolling, or utility injection.
// The unnumbered manifesto and compatibility pages keep ordinary reading links.
if (currentIndex !== -1) {
  document.documentElement.dataset.keyboardNav = "ready";
  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    var target = event.target;
    if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
    // Let keyboard users scroll an explicitly focusable table region.
    if (target && target.closest && target.closest('[role="region"]')) return;

    var destination = null;
    if (event.key === "ArrowLeft") destination = document.querySelector(".page-nav .prev");
    if (event.key === "ArrowRight") destination = document.querySelector(".page-nav .next");
    if (destination && destination.href) {
      event.preventDefault();
      window.location.href = destination.href;
    }
  });
}
