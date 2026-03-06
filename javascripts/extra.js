// Extra JavaScript for amplihack documentation

document.addEventListener("DOMContentLoaded", function () {
  // Add copy button functionality enhancement
  const copyButtons = document.querySelectorAll(".md-clipboard");
  copyButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Add visual feedback
      const icon = this.querySelector(".md-clipboard__icon");
      if (icon) {
        icon.style.color = "#4caf50";
        setTimeout(() => {
          icon.style.color = "";
        }, 2000);
      }
    });
  });

  // Add smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });

  // Add "Back to Top" button
  const backToTopButton = document.createElement("button");
  backToTopButton.innerHTML = "↑";
  backToTopButton.className = "back-to-top";
  backToTopButton.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: var(--md-primary-fg-color);
        color: white;
        border: none;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        font-size: 24px;
        cursor: pointer;
        display: none;
        z-index: 1000;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        transition: opacity 0.3s;
    `;
  document.body.appendChild(backToTopButton);

  // Show/hide back to top button
  window.addEventListener("scroll", function () {
    if (window.pageYOffset > 300) {
      backToTopButton.style.display = "block";
    } else {
      backToTopButton.style.display = "none";
    }
  });

  backToTopButton.addEventListener("click", function () {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  });

  // Add external link indicators
  document.querySelectorAll('a[href^="http"]').forEach((link) => {
    if (!link.hostname.includes(window.location.hostname)) {
      link.setAttribute("target", "_blank");
      link.setAttribute("rel", "noopener noreferrer");
      link.innerHTML += ' <span style="font-size:0.8em">↗</span>';
    }
  });

  // Enhance command code blocks
  document.querySelectorAll("pre code").forEach((block) => {
    const text = block.textContent;
    if (text.startsWith("/") || text.startsWith("make ")) {
      block.parentElement.classList.add("command-block");
    }
  });

  console.log("amplihack documentation enhancements loaded");
});
