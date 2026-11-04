const form = document.querySelector("#extract-form");
const documentType = document.querySelector("#document-type");
const documentText = document.querySelector("#document-text");
const pdfFileInput = document.querySelector("#pdf-file");
const dropzone = document.querySelector("#dropzone");
const selectedFile = document.querySelector("#selected-file");
const fileName = document.querySelector("#file-name");
const fileSize = document.querySelector("#file-size");
const characterCount = document.querySelector("#character-count");
const formError = document.querySelector("#form-error");
const submitButton = document.querySelector("#submit-button");
const submitLabel = submitButton.querySelector(".submit-label");
const resultContent = document.querySelector("#result-content");
const emptyState = document.querySelector("#empty-state");
const loadingState = document.querySelector("#loading-state");
const resultOutput = document.querySelector("#result-output");
const resultJson = document.querySelector("#result-json");
const resultCaption = document.querySelector("#result-caption");
const copyButton = document.querySelector("#copy-result");
const connectionStatus = document.querySelector("#connection-status");
const connectionLabel = document.querySelector("#connection-label");
const pdfTab = document.querySelector("#pdf-tab");
const textTab = document.querySelector("#text-tab");
const pdfPanel = document.querySelector("#pdf-panel");
const textPanel = document.querySelector("#text-panel");
const maxPdfBytes = 10 * 1024 * 1024;
let selectedPdf = null;
let inputMode = "pdf";

const examples = {
  resume: `Jane Doe
Email: jane.doe@example.com
Phone: +1 555 010 2040
Skills: Python, FastAPI, SQL
Education: BSc Computer Science, Example University, 2022
Experience: Software Developer at Acme, 2022–2025`,
  invoice: `Invoice: INV-1001
Date: 2025-01-15
From: Example Supply
To: Acme Ltd
2 x Widget at $12.50: $25.00
Subtotal: $25.00
Tax: $2.50
Total: $27.50 USD`,
};

function updateCharacterCount() {
  const count = documentText.value.length;
  characterCount.textContent = `${count.toLocaleString()} ${count === 1 ? "character" : "characters"}`;
}

function showError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function formatFileSize(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function showSelectedPdf(file) {
  formError.hidden = true;
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showError("Please choose a PDF file.");
    return;
  }
  if (file.size > maxPdfBytes) {
    showError("This PDF is larger than the 10 MB limit.");
    return;
  }
  if (file.size === 0) {
    showError("This PDF is empty. Choose another file.");
    return;
  }

  selectedPdf = file;
  fileName.textContent = file.name;
  fileSize.textContent = formatFileSize(file.size);
  selectedFile.hidden = false;
  dropzone.hidden = true;
}

function clearSelectedPdf() {
  selectedPdf = null;
  pdfFileInput.value = "";
  selectedFile.hidden = true;
  dropzone.hidden = false;
}

function setInputMode(mode) {
  inputMode = mode;
  const isPdf = mode === "pdf";
  pdfTab.classList.toggle("is-active", isPdf);
  textTab.classList.toggle("is-active", !isPdf);
  pdfTab.setAttribute("aria-selected", String(isPdf));
  textTab.setAttribute("aria-selected", String(!isPdf));
  pdfPanel.hidden = !isPdf;
  textPanel.hidden = isPdf;
  formError.hidden = true;
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitLabel.textContent = isLoading ? "Extracting..." : "Extract data";
  resultContent.setAttribute("aria-busy", String(isLoading));
  emptyState.hidden = true;
  resultOutput.hidden = true;
  loadingState.hidden = !isLoading;
  if (!isLoading && !resultJson.textContent) {
    emptyState.hidden = false;
  }
}

documentText.addEventListener("input", updateCharacterCount);
pdfTab.addEventListener("click", () => setInputMode("pdf"));
textTab.addEventListener("click", () => setInputMode("text"));
dropzone.addEventListener("click", () => pdfFileInput.click());
pdfFileInput.addEventListener("change", () => showSelectedPdf(pdfFileInput.files[0]));
document.querySelector("#remove-file").addEventListener("click", clearSelectedPdf);

for (const eventName of ["dragenter", "dragover"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-dragging");
  });
}
dropzone.addEventListener("drop", (event) => {
  showSelectedPdf(event.dataTransfer.files[0]);
});

document.querySelector("#clear-text").addEventListener("click", () => {
  documentText.value = "";
  updateCharacterCount();
  documentText.focus();
  formError.hidden = true;
});

document.querySelector("#load-example").addEventListener("click", () => {
  documentText.value = examples[documentType.value];
  updateCharacterCount();
  formError.hidden = true;
  documentText.focus();
});

documentType.addEventListener("change", () => {
  documentText.placeholder = `Paste the text from your ${documentType.value} here...`;
  formError.hidden = true;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.hidden = true;
  resultJson.textContent = "";
  copyButton.disabled = true;

  if (inputMode === "pdf" && !selectedPdf) {
    showError("Choose a PDF file before extracting.");
    dropzone.focus();
    return;
  }
  if (inputMode === "text" && !documentText.value.trim()) {
    showError("Please paste some document text before extracting.");
    documentText.focus();
    return;
  }

  setLoading(true);
  try {
    const body = inputMode === "pdf"
      ? (() => {
          const formData = new FormData();
          formData.append("file", selectedPdf);
          return formData;
        })()
      : JSON.stringify({ text: documentText.value });
    const response = await fetch(
      inputMode === "pdf"
        ? `/extract/${documentType.value}/pdf`
        : `/extract/${documentType.value}`,
      {
        method: "POST",
        headers: inputMode === "text" ? { "Content-Type": "application/json" } : {},
        body,
      },
    );
    const payload = await response.json();

    if (!response.ok) {
      const detail = payload.detail;
      const message = typeof detail === "string" ? detail : Array.isArray(detail)
        ? detail.map((item) => item.msg || JSON.stringify(item)).join("; ")
        : "The extraction request could not be completed.";
      throw new Error(message);
    }

    resultJson.textContent = JSON.stringify(payload, null, 2);
    resultCaption.textContent = `${documentType.value === "resume" ? "Resume" : "Invoice"} extraction complete`;
    resultOutput.hidden = false;
    loadingState.hidden = true;
    emptyState.hidden = true;
    copyButton.disabled = false;
  } catch (error) {
    loadingState.hidden = true;
    emptyState.hidden = false;
    showError(error instanceof TypeError
      ? "Could not connect to the API. Check that the server is running and try again."
      : error.message);
  } finally {
    submitButton.disabled = false;
    submitLabel.textContent = "Extract data";
    resultContent.setAttribute("aria-busy", "false");
  }
});

copyButton.addEventListener("click", async () => {
  if (!resultJson.textContent) return;
  try {
    await navigator.clipboard.writeText(resultJson.textContent);
    copyButton.querySelector("span").textContent = "Copied!";
    window.setTimeout(() => {
      copyButton.querySelector("span").textContent = "Copy JSON";
    }, 1400);
  } catch {
    showError("Could not copy automatically. Select and copy the JSON instead.");
  }
});

async function checkApiStatus() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("API unavailable");
    connectionStatus.classList.add("is-online");
    connectionLabel.textContent = "API connected";
  } catch {
    connectionStatus.classList.add("is-offline");
    connectionLabel.textContent = "API unavailable";
  }
}

updateCharacterCount();
checkApiStatus();
