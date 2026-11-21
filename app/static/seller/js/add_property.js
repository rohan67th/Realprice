/* add_property.js — Add Property wizard page-specific logic */

let currentStep = 1;
const totalSteps = 4;

// Cache object for DOM elements
let DOM = {};

// Helper to format Indian Rupee prices
const formatRupeePrice = n => {
  if (isNaN(n) || n <= 0) return '₹0';
  return n >= 1e7 ? '₹' + (n / 1e7).toFixed(2) + 'Cr' :
         n >= 1e5 ? '₹' + (n / 1e5).toFixed(2) + 'L' :
         '₹' + Number(n).toLocaleString('en-IN');
};

/* ---------- INITIALIZE ELEMENTS & EVENTS ---------- */
document.addEventListener('DOMContentLoaded', () => {
  cacheElements();
  setupWizardButtons();
  setupGeocoding();
  setupImageDropzones();
  setupCharCounter();
  setupSidebarSync();
  setupFormSubmit();
  
  // Set initial wizard state
  updateWizardState();
});

function cacheElements() {
  DOM = {
    form: $('form'),
    btnPrev: $('#btn-prev'),
    btnNext: $('#btn-next'),
    btnSubmit: $('#btn-submit'),
    fetchBtn: $('#fetch-location'),
    description: $('#description'),
    charCount: $('#char-count'),
    validationAlert: $('#validation-alert'),
    reviewInfo: $('#review-info'),

    // Step 1 Inputs
    propertyType: $('#property_type'),
    address: $('#address'),
    location: $('#location'),
    latitude: $('#latitude'),
    longitude: $('#longitude'),

    // Step 2 Inputs
    price: $('#price'),
    areaSqft: $('#area_sqft'),
    bedrooms: $('#bedrooms'),
    bathrooms: $('#bathrooms'),
    status: $('#status'),
    features: $('#features'),

    // Step 3 Inputs
    mainImage: $('#main_image'),
    image1: $('#image_1'),
    image2: $('#image_2'),
    image3: $('#image_3'),

    // Sidebar Summary elements
    summaryType: $('#summary-type'),
    summaryLocation: $('#summary-location'),
    summaryStatus: $('#summary-status'),
    summaryPrice: $('#summary-price'),
    summaryImagesCount: $('#summary-images-count'),
    summaryProgressBar: $('#summary-progress-bar'),
    summaryProgressText: $('#summary-progress-text')
  };
}

/* ---------- WIZARD CONTROL ---------- */
function setupWizardButtons() {
  if (DOM.btnNext) DOM.btnNext.addEventListener('click', navigateNextStep);
  if (DOM.btnPrev) DOM.btnPrev.addEventListener('click', navigatePrevStep);
}

function updateWizardState() {
  // Toggle step panels visibility
  $$('.step-panel').forEach(panel => {
    const step = parseInt(panel.dataset.step);
    const isCurrent = (step === currentStep);
    panel.classList.toggle('hidden', !isCurrent);

    // Manage 'required' attributes dynamically to prevent browser focus errors
    $$('input, select, textarea', panel).forEach(el => {
      if (isCurrent) {
        if (el.dataset.required === "true") {
          el.required = true;
        }
      } else {
        if (el.required) {
          el.dataset.required = "true";
          el.required = false;
        }
      }
    });
  });

  // Update top wizard indicator highlights
  $$('.step-indicator-item').forEach(indicator => {
    const step = parseInt(indicator.dataset.step);
    const line = indicator.querySelector('.indicator-line');
    const circle = indicator.querySelector('.indicator-circle');
    const text = indicator.querySelector('.indicator-text');

    if (step < currentStep) {
      circle.className = "indicator-circle h-9 w-9 rounded-full bg-success-600 text-white flex items-center justify-center font-bold text-sm shadow-glow";
      circle.innerHTML = `<i class="ri-check-line"></i>`;
      if (text) text.className = "indicator-text text-xs font-semibold text-ink-900 dark:text-white mt-2";
      if (line) line.className = "indicator-line hidden sm:block flex-1 h-1 bg-success-600 -mt-5";
    } else if (step === currentStep) {
      circle.className = "indicator-circle h-9 w-9 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold text-sm shadow-glow";
      circle.innerHTML = `${step}`;
      if (text) text.className = "indicator-text text-xs font-bold text-brand-600 mt-2";
      if (line) line.className = "indicator-line hidden sm:block flex-1 h-1 bg-ink-250 dark:bg-ink-800 -mt-5";
    } else {
      circle.className = "indicator-circle h-9 w-9 rounded-full bg-ink-100 dark:bg-ink-800 text-ink-400 flex items-center justify-center font-bold text-sm";
      circle.innerHTML = `${step}`;
      if (text) text.className = "indicator-text text-xs font-semibold text-ink-400 mt-2";
      if (line) line.className = "indicator-line hidden sm:block flex-1 h-1 bg-ink-100 dark:bg-ink-800 -mt-5";
    }
  });

  // Toggle button states
  if (DOM.btnPrev) DOM.btnPrev.classList.toggle('hidden', currentStep === 1);
  if (currentStep === totalSteps) {
    if (DOM.btnNext) DOM.btnNext.classList.add('hidden');
    if (DOM.btnSubmit) DOM.btnSubmit.classList.remove('hidden');
    generateReviewSummary();
  } else {
    if (DOM.btnNext) DOM.btnNext.classList.remove('hidden');
    if (DOM.btnSubmit) DOM.btnSubmit.classList.add('hidden');
  }

  updateProgressTracker();
}

function navigateNextStep() {
  if (validateActivePanel(currentStep)) {
    currentStep = Math.min(totalSteps, currentStep + 1);
    updateWizardState();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function navigatePrevStep() {
  currentStep = Math.max(1, currentStep - 1);
  updateWizardState();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ---------- JS CLIENT SIDE VALIDATION ---------- */
function validateActivePanel(step) {
  let isStepValid = true;
  let selectorList = [];

  if (step === 1) {
    selectorList = [DOM.propertyType, DOM.address, DOM.location];
  } else if (step === 2) {
    selectorList = [DOM.price];
  } else if (step === 3) {
    selectorList = [DOM.mainImage];
  }

  selectorList.forEach(el => {
    if (el) {
      const isSelectEmpty = (el.tagName === 'SELECT' && !el.value);
      const isFileEmpty = (el.type === 'file' && (!el.files || el.files.length === 0));
      const isTextEmpty = (el.type !== 'file' && el.tagName !== 'SELECT' && (!el.value || el.value.trim() === ''));

      if (isSelectEmpty || isFileEmpty || isTextEmpty) {
        el.classList.add('border-danger-500', 'focus:ring-danger-500');
        // Handle drag and drop zone validation high-lighting if input is file
        if (el.type === 'file') {
          const dropzone = $('#dropzone-main');
          if (dropzone) dropzone.classList.add('border-danger-500', 'bg-danger-50/10');
        }
        isStepValid = false;
      } else {
        el.classList.remove('border-danger-500', 'focus:ring-danger-500');
        if (el.type === 'file') {
          const dropzone = $('#dropzone-main');
          if (dropzone) dropzone.classList.remove('border-danger-500', 'bg-danger-50/10');
        }
      }
    }
  });

  if (!isStepValid && DOM.validationAlert) {
    DOM.validationAlert.classList.remove('hidden');
    setTimeout(() => {
      if (DOM.validationAlert) DOM.validationAlert.classList.add('hidden');
    }, 4000);
  }

  return isStepValid;
}

/* ---------- REVIEW PANEL SUMMARY GENERATION ---------- */
function generateReviewSummary() {
  if (!DOM.reviewInfo) return;

  const type = DOM.propertyType ? DOM.propertyType.value : '';
  const address = DOM.address ? DOM.address.value : '';
  const location = DOM.location ? DOM.location.value : '';
  const lat = DOM.latitude && DOM.latitude.value ? DOM.latitude.value : 'Not provided';
  const lon = DOM.longitude && DOM.longitude.value ? DOM.longitude.value : 'Not provided';
  const area = DOM.areaSqft && DOM.areaSqft.value ? DOM.areaSqft.value + ' sq ft' : 'Not specified';
  const beds = DOM.bedrooms && DOM.bedrooms.value ? DOM.bedrooms.value : '0';
  const baths = DOM.bathrooms && DOM.bathrooms.value ? DOM.bathrooms.value : '0';
  const price = DOM.price && DOM.price.value ? formatRupeePrice(parseFloat(DOM.price.value)) : '₹0';
  const status = DOM.status ? DOM.status.value : 'Available';
  const desc = DOM.description && DOM.description.value ? DOM.description.value : 'No description provided';
  const feats = DOM.features && DOM.features.value ? DOM.features.value : 'None specified';

  DOM.reviewInfo.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
      <div class="space-y-3">
        <h4 class="font-bold text-ink-900 dark:text-white uppercase tracking-wider text-xs">Basic Information</h4>
        <p><span class="text-ink-400">Property Type:</span> <strong class="text-ink-900 dark:text-white">${type}</strong></p>
        <p><span class="text-ink-400">Address:</span> <strong class="text-ink-900 dark:text-white">${address}</strong></p>
        <p><span class="text-ink-400">Location:</span> <strong class="text-ink-900 dark:text-white">${location}</strong></p>
        <p><span class="text-ink-400">Coordinates:</span> <strong class="text-ink-700 dark:text-ink-200">${lat}, ${lon}</strong></p>
      </div>
      <div class="space-y-3">
        <h4 class="font-bold text-ink-900 dark:text-white uppercase tracking-wider text-xs">Listing Details</h4>
        <p><span class="text-ink-400">Price:</span> <strong class="text-brand-600 dark:text-brand-400">${price}</strong></p>
        <p><span class="text-ink-400">Area:</span> <strong class="text-ink-900 dark:text-white">${area}</strong></p>
        <p><span class="text-ink-400">Rooms:</span> <strong class="text-ink-900 dark:text-white">${beds} Beds · ${baths} Baths</strong></p>
        <p><span class="text-ink-400">Status:</span> <strong class="text-ink-900 dark:text-white">${status}</strong></p>
      </div>
      <div class="md:col-span-2 space-y-3">
        <h4 class="font-bold text-ink-900 dark:text-white uppercase tracking-wider text-xs">Features & Description</h4>
        <p><span class="text-ink-400">Features:</span> <span class="text-ink-700 dark:text-ink-300 font-medium">${feats}</span></p>
        <div class="p-4 rounded-xl bg-ink-50 dark:bg-ink-900/50 text-ink-700 dark:text-ink-300 text-xs italic leading-relaxed">
          "${desc}"
        </div>
      </div>
    </div>
  `;
}

/* ---------- LATITUDE / LONGITUDE GEOCODING ---------- */
function setupGeocoding() {
  if (!DOM.fetchBtn) return;

  DOM.fetchBtn.addEventListener('click', () => {
    const locVal = DOM.location ? DOM.location.value : '';
    if (!locVal) {
      alert("Please enter a location first.");
      return;
    }

    DOM.fetchBtn.innerHTML = `<i class="ri-loader-4-line animate-spin"></i> Fetching...`;
    DOM.fetchBtn.disabled = true;

    const proxyUrl = "https://api.allorigins.win/raw?url=";
    const queryUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(locVal)}`;
    const url = proxyUrl + encodeURIComponent(queryUrl);

    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (data && data.length > 0) {
          if (DOM.latitude) DOM.latitude.value = data[0].lat;
          if (DOM.longitude) DOM.longitude.value = data[0].lon;
          updateProgressTracker();
        } else {
          alert("Location not found. Try a more specific location details.");
        }
      })
      .catch(error => {
        console.error("Geocoding error:", error);
        alert("Error fetching coordinates.");
      })
      .finally(() => {
        DOM.fetchBtn.innerHTML = `Fetch Coordinates`;
        DOM.fetchBtn.disabled = false;
      });
  });
}

/* ---------- DRAG & DROP PHOTO DROPOZNES ---------- */
function setupImageDropzones() {
  const uploadZones = [
    { zone: '#dropzone-main', input: DOM.mainImage, preview: '#preview-main', clear: '#clear-main' },
    { zone: '#dropzone-img1', input: DOM.image1, preview: '#preview-img1', clear: '#clear-img1' },
    { zone: '#dropzone-img2', input: DOM.image2, preview: '#preview-img2', clear: '#clear-img2' },
    { zone: '#dropzone-img3', input: DOM.image3, preview: '#preview-img3', clear: '#clear-img3' }
  ];

  uploadZones.forEach(({ zone, input, preview, clear }) => {
    const zEl = $(zone);
    const pEl = $(preview);
    const cEl = $(clear);

    if (!zEl || !input) return;

    zEl.addEventListener('click', (e) => {
      if (e.target.closest(clear)) return;
      input.click();
    });

    zEl.addEventListener('dragover', (e) => {
      e.preventDefault();
      zEl.classList.add('border-brand-500', 'bg-brand-50/20', 'dark:bg-brand-900/10');
    });

    zEl.addEventListener('dragleave', () => {
      zEl.classList.remove('border-brand-500', 'bg-brand-50/20', 'dark:bg-brand-900/10');
    });

    zEl.addEventListener('drop', (e) => {
      e.preventDefault();
      zEl.classList.remove('border-brand-500', 'bg-brand-50/20', 'dark:bg-brand-900/10');
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        renderImageThumbnail(input.files[0], zEl, pEl, cEl);
      }
    });

    input.addEventListener('change', () => {
      if (input.files.length) {
        renderImageThumbnail(input.files[0], zEl, pEl, cEl);
      }
    });

    if (cEl) {
      cEl.addEventListener('click', (e) => {
        e.stopPropagation();
        input.value = '';
        zEl.querySelector('.placeholder-content').classList.remove('hidden');
        pEl.classList.add('hidden');
        pEl.style.backgroundImage = 'none';
        cEl.classList.add('hidden');
        updateProgressTracker();
      });
    }
  });
}

function renderImageThumbnail(file, zone, preview, clear) {
  if (!file.type.startsWith('image/')) {
    alert("Please upload image files only.");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    zone.querySelector('.placeholder-content').classList.add('hidden');
    preview.classList.remove('hidden');
    preview.style.backgroundImage = `url('${e.target.result}')`;
    clear.classList.remove('hidden');
    updateProgressTracker();
  };
  reader.readAsDataURL(file);
}

/* ---------- DESCRIPTION TEXT COUNTER ---------- */
function setupCharCounter() {
  if (!DOM.description || !DOM.charCount) return;

  DOM.description.addEventListener('input', () => {
    const len = DOM.description.value.length;
    DOM.charCount.textContent = `${len} / 1000 characters`;
    DOM.charCount.classList.toggle('text-danger-500', len > 1000);
    updateProgressTracker();
  });
}

/* ---------- SIDEBAR SYNC & COMPLETION ---------- */
function setupSidebarSync() {
  const syncMappings = [
    { source: DOM.propertyType, dest: DOM.summaryType, def: 'Not specified' },
    { source: DOM.location, dest: DOM.summaryLocation, def: 'Not specified' },
    { source: DOM.status, dest: DOM.summaryStatus, def: 'Available' },
    { source: DOM.price, dest: DOM.summaryPrice, def: '₹0', isCurrency: true }
  ];

  syncMappings.forEach(({ source, dest, def, isCurrency }) => {
    if (!source || !dest) return;
    source.addEventListener('input', () => {
      const val = source.value;
      if (!val || val.trim() === '') {
        dest.textContent = def;
      } else if (isCurrency) {
        dest.textContent = formatRupeePrice(parseFloat(val));
      } else {
        dest.textContent = val;
      }
      updateProgressTracker();
    });
  });
}

function updateProgressTracker() {
  const checkFields = [
    DOM.propertyType, DOM.address, DOM.location, DOM.latitude, DOM.longitude,
    DOM.areaSqft, DOM.bedrooms, DOM.bathrooms, DOM.features, DOM.price,
    DOM.description, DOM.status, DOM.mainImage
  ];

  let filled = 0;
  checkFields.forEach(el => {
    if (el) {
      if (el.type === 'file') {
        if (el.files && el.files.length > 0) filled++;
      } else {
        if (el.value && el.value.trim() !== '') filled++;
      }
    }
  });

  const completionPercent = Math.round((filled / checkFields.length) * 100);

  if (DOM.summaryProgressBar) DOM.summaryProgressBar.style.width = `${completionPercent}%`;
  if (DOM.summaryProgressText) DOM.summaryProgressText.textContent = `${completionPercent}% Complete`;

  // Gallery photo counting
  let uploads = 0;
  [DOM.mainImage, DOM.image1, DOM.image2, DOM.image3].forEach(input => {
    if (input && input.files && input.files.length > 0) uploads++;
  });
  if (DOM.summaryImagesCount) DOM.summaryImagesCount.textContent = `${uploads} / 4 Images`;
}

/* ---------- STANDARD SUBMISSION & LOADER ---------- */
function setupFormSubmit() {
  if (!DOM.form) return;

  DOM.form.addEventListener('submit', (e) => {
    // Perform safety validations
    if (!validateActivePanel(1) || !validateActivePanel(2) || !validateActivePanel(3)) {
      e.preventDefault();
      return;
    }

    if (DOM.btnSubmit) {
      DOM.btnSubmit.disabled = true;
      DOM.btnSubmit.innerHTML = `<i class="ri-loader-4-line animate-spin text-lg"></i> Publishing...`;
    }
  });
}
