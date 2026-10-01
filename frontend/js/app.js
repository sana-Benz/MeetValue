// ========================================
// API Configuration
// ========================================
// Values come from js/config.js (gitignored; template in js/config.example.js),
// loaded before this file in index.html.
const { API_BASE_URL, RECOMMENDATIONS_API_KEY } = window.MEETVALUE_CONFIG;

// Default hourly rates by seniority, used to auto-fill the per-attendee rate
// field. MAINTENANCE NOTE: duplicated from backend/shared/constants.py —
// the frontend has no build step to import it directly, so keep both in sync.
const DEFAULT_RATES = {
  junior: 50,
  'mid-level': 100,
  senior: 200,
  executive: 400,
};

const MAX_ATTENDEE_TEXT_LENGTH = 100;

// ========================================
// DOM Elements
// ========================================
const logoBtn = document.getElementById('logoBtn');
const landingSection = document.getElementById('landingSection');
const startCalculatingBtn = document.getElementById('startCalculatingBtn');
const newMeetingBtn = document.getElementById('newMeetingBtn');
const meetingForm = document.getElementById('meetingForm');
const subjectInput = document.getElementById('subject');
const durationInput = document.getElementById('duration');
const isRecurringCheckbox = document.getElementById('isRecurring');
const recurringFieldsGroup = document.getElementById('recurringFieldsGroup');
const recurringFrequencyInput = document.getElementById('recurringFrequency');
const recurringUnitSelect = document.getElementById('recurringUnit');
const recurringResult = document.getElementById('recurringResult');
const recurringMonthlyValue = document.getElementById('recurringMonthlyValue');
const recurringAnnualValue = document.getElementById('recurringAnnualValue');
const attendeesList = document.getElementById('attendeesList');
const addAttendeeBtn = document.getElementById('addAttendeeBtn');
const calculateBtn = document.getElementById('calculateBtn');
const errorContainer = document.getElementById('errorContainer');
const errorTitle = document.getElementById('errorTitle');
const errorMessage = document.getElementById('errorMessage');
const errorCloseBtn = document.querySelector('.error-close');
const loadingIndicator = document.getElementById('loadingIndicator');
const resultsSection = document.getElementById('resultsSection');
const costResult = document.getElementById('costResult');
const totalCostDisplay = document.getElementById('totalCostDisplay');
const breakdownTableBody = document.getElementById('breakdownTableBody');
const recommendationsList = document.getElementById('recommendationsList');
const recommendationsError = document.getElementById('recommendationsError');
const totalSavingsBanner = document.getElementById('totalSavingsBanner');
const totalSavingsAmount = document.getElementById('totalSavingsAmount');
const totalSavingsPercent = document.getElementById('totalSavingsPercent');
const yearSpan = document.getElementById('year');

// Error spans for inline validation
const errorSpans = {
  subject: document.querySelector('.error-subject'),
  duration: document.querySelector('.error-duration'),
  attendees: document.querySelector('.error-attendees'),
};

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
  // Footer copyright year — never goes stale
  yearSpan.textContent = new Date().getFullYear();

  // Add initial attendee row
  addAttendeeRow();

  // Event listeners
  meetingForm.addEventListener('submit', handleFormSubmit);
  addAttendeeBtn.addEventListener('click', addAttendeeRow);
  errorCloseBtn.addEventListener('click', hideError);
  newMeetingBtn.addEventListener('click', resetForm);

  // Landing navigation: CTA scrolls down to the form, logo always scrolls
  // back up to the landing section — no section show/hide state needed
  startCalculatingBtn.addEventListener('click', () => {
    meetingForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  logoBtn.addEventListener('click', () => {
    landingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // Real-time validation
  subjectInput.addEventListener('blur', validateSubject);
  durationInput.addEventListener('blur', validateDuration);

  // Show/hide the frequency fields based on the recurring toggle
  isRecurringCheckbox.addEventListener('change', () => {
    recurringFieldsGroup.classList.toggle('hidden', !isRecurringCheckbox.checked);
  });
});

// ========================================
// Form Validation
// ========================================

function validateSubject() {
  const subject = subjectInput.value.trim();
  if (!subject) {
    errorSpans.subject.textContent = 'Subject is required';
    return false;
  }
  errorSpans.subject.textContent = '';
  return true;
}

function validateDuration() {
  const duration = parseInt(durationInput.value, 10);
  if (isNaN(duration) || duration < 15 || duration > 240) {
    errorSpans.duration.textContent = 'Duration must be between 15 and 240 minutes';
    return false;
  }
  errorSpans.duration.textContent = '';
  return true;
}

function validateAttendees() {
  const attendeeRows = attendeesList.querySelectorAll('.attendee-row');
  if (attendeeRows.length === 0) {
    errorSpans.attendees.textContent = 'At least one attendee is required';
    return false;
  }

  // Validate each attendee
  for (const row of attendeeRows) {
    const nameInput = row.querySelector('.attendee-name');
    const roleInput = row.querySelector('.attendee-role');
    const senioritySelect = row.querySelector('.attendee-seniority');
    const rateInput = row.querySelector('.attendee-rate');
    const name = nameInput.value.trim();
    const role = roleInput.value.trim();
    const seniority = senioritySelect.value;
    const rate = parseFloat(rateInput.value);

    if (!name || !seniority) {
      errorSpans.attendees.textContent = 'All attendees must have a name and seniority level';
      return false;
    }

    if (!role) {
      errorSpans.attendees.textContent = 'All attendees must have a role';
      return false;
    }

    if (role.length > MAX_ATTENDEE_TEXT_LENGTH) {
      errorSpans.attendees.textContent = `Role must be ${MAX_ATTENDEE_TEXT_LENGTH} characters or fewer`;
      return false;
    }

    if (isNaN(rate) || rate <= 0) {
      errorSpans.attendees.textContent = 'All attendees must have a valid hourly rate greater than 0';
      return false;
    }
  }

  errorSpans.attendees.textContent = '';
  return true;
}

function validateForm() {
  const isSubjectValid = validateSubject();
  const isDurationValid = validateDuration();
  const isAttendeesValid = validateAttendees();

  return isSubjectValid && isDurationValid && isAttendeesValid;
}

// ========================================
// Attendee Management
// ========================================

function addAttendeeRow() {
  const template = document.getElementById('attendeeRowTemplate');
  const clone = template.content.cloneNode(true);
  const removeBtn = clone.querySelector('.btn-remove-attendee');
  const senioritySelect = clone.querySelector('.attendee-seniority');
  const rateInput = clone.querySelector('.attendee-rate');

  // Add remove functionality
  removeBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const row = removeBtn.closest('.attendee-row');
    row.remove();
    clearInlineError('attendees');
  });

  // Auto-fill the rate field with the seniority's default; the user can
  // still edit it afterward to override it for this attendee
  senioritySelect.addEventListener('change', () => {
    const defaultRate = DEFAULT_RATES[senioritySelect.value];
    if (defaultRate !== undefined) {
      rateInput.value = defaultRate;
    }
  });

  attendeesList.appendChild(clone);
}

// ========================================
// Error Handling
// ========================================

function showError(title, message) {
  errorTitle.textContent = title;
  errorMessage.textContent = message;
  errorContainer.classList.add('visible');
  errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
  errorContainer.classList.remove('visible');
}

function clearInlineError(fieldName) {
  if (errorSpans[fieldName]) {
    errorSpans[fieldName].textContent = '';
  }
}

// ========================================
// Loading State
// ========================================

function showLoading() {
  loadingIndicator.classList.add('visible');
  calculateBtn.disabled = true;
}

function hideLoading() {
  loadingIndicator.classList.remove('visible');
  calculateBtn.disabled = false;
}

// ========================================
// API Calls
// ========================================

async function calculateCost(meetingData) {
  try {
    const response = await fetch(`${API_BASE_URL}/calculate-cost`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(meetingData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error || `Cost calculation failed (${response.status})`
      );
    }

    return await response.json();
  } catch (error) {
    throw new Error(`Cost calculation error: ${error.message}`);
  }
}

async function getRecommendations(meetingData) {
  try {
    const response = await fetch(`${API_BASE_URL}/get-recommendations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': RECOMMENDATIONS_API_KEY,
      },
      body: JSON.stringify(meetingData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      // For recommendations, we don't throw on failure - we'll show the fallback
      return null;
    }

    return await response.json();
  } catch (error) {
    // Silently fail for recommendations - they're optional
    console.warn('Recommendations fetch error:', error.message);
    return null;
  }
}

// ========================================
// Data Collection
// ========================================

function collectFormData() {
  const attendeeRows = attendeesList.querySelectorAll('.attendee-row');
  const attendees = [];

  for (const row of attendeeRows) {
    const name = row.querySelector('.attendee-name').value.trim();
    const role = row.querySelector('.attendee-role').value.trim();
    const seniority = row.querySelector('.attendee-seniority').value;
    const hourly_rate = parseFloat(row.querySelector('.attendee-rate').value);
    if (name && seniority && role && !isNaN(hourly_rate)) {
      attendees.push({ name, role, seniority, hourly_rate });
    }
  }

  return {
    subject: subjectInput.value.trim(),
    duration_minutes: parseInt(durationInput.value, 10),
    attendees,
  };
}

// ========================================
// Result Rendering
// ========================================

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function animateCostCounter(el, targetValue, duration = 800) {
  const startTime = performance.now();

  function tick(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    // Ease-out so the count-up settles into the final number smoothly
    const eased = 1 - Math.pow(1 - progress, 2);
    el.textContent = formatCurrency(targetValue * eased);

    if (progress < 1) {
      requestAnimationFrame(tick);
    } else {
      el.textContent = formatCurrency(targetValue);
    }
  }

  requestAnimationFrame(tick);
}

function displayRecurringProjection(totalCost) {
  // Unchecked (the default): no projection, single-meeting cost only —
  // behaves exactly as before this feature existed.
  if (!isRecurringCheckbox.checked) {
    recurringResult.classList.add('hidden');
    return;
  }

  const frequency = parseInt(recurringFrequencyInput.value, 10);
  if (isNaN(frequency) || frequency < 1) {
    recurringResult.classList.add('hidden');
    return;
  }

  let monthlyCost;
  let annualCost;

  if (recurringUnitSelect.value === 'week') {
    const weeklyCost = totalCost * frequency;
    monthlyCost = weeklyCost * 4.33;
    annualCost = weeklyCost * 52;
  } else {
    // 'month'
    monthlyCost = totalCost * frequency;
    annualCost = monthlyCost * 12;
  }

  recurringMonthlyValue.textContent = formatCurrency(monthlyCost);
  recurringAnnualValue.textContent = formatCurrency(annualCost);
  recurringResult.classList.remove('hidden');
}

function displayCostResult(data) {
  // Fade/scale the headline container in, restarting the animation even if
  // results were already visible from a previous calculation
  costResult.classList.remove('animate-in');
  void costResult.offsetWidth; // force reflow so the animation can restart
  costResult.classList.add('animate-in');

  // Count the total cost up from 0 instead of snapping to the final value
  animateCostCounter(totalCostDisplay, data.total_cost);

  displayRecurringProjection(data.total_cost);

  // Clear and populate breakdown table
  breakdownTableBody.innerHTML = '';
  for (const item of data.breakdown) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${escapeHtml(item.attendee_name)}</td>
      <td>${escapeHtml(item.role)}</td>
      <td>${escapeHtml(item.seniority)}</td>
      <td>${formatCurrency(item.hourly_rate)}</td>
      <td>${formatCurrency(item.cost_contribution)}</td>
    `;
    breakdownTableBody.appendChild(row);
  }
}

function displayRecommendations(data, totalCost) {
  recommendationsList.innerHTML = '';
  recommendationsError.classList.add('hidden');
  totalSavingsBanner.classList.add('hidden');

  if (!data || !data.recommendations || data.recommendations.length === 0) {
    recommendationsError.classList.remove('hidden');
    return;
  }

  for (const rec of data.recommendations) {
    const template = document.getElementById('recommendationTemplate');
    const clone = template.content.cloneNode(true);

    const categoryEl = clone.querySelector('.recommendation-category');
    const savingsEl = clone.querySelector('.recommendation-savings');
    const textEl = clone.querySelector('.recommendation-text');

    categoryEl.textContent = rec.category.replace(/_/g, ' ');
    savingsEl.textContent = `Save ${formatCurrency(rec.estimated_savings)}`;
    textEl.textContent = rec.suggestion;

    recommendationsList.appendChild(clone);
  }

  // Headline takeaway: the single best recommendation, not a sum across all
  // of them — categories like partial_attendance and duration_reduction can
  // overlap the same time/people, so adding their savings together would
  // double-count. Hidden when there's nothing worth highlighting (e.g. the
  // $0 defaults shown when Claude's response couldn't be parsed).
  const bestSavings = data.recommendations.reduce(
    (best, rec) => Math.max(best, Number(rec.estimated_savings) || 0),
    0
  );

  if (bestSavings > 0) {
    totalSavingsAmount.textContent = formatCurrency(bestSavings);
    totalSavingsPercent.textContent = totalCost > 0
      ? `${((bestSavings / totalCost) * 100).toFixed(1)}% of meeting cost`
      : '';
    totalSavingsBanner.classList.remove('hidden');
  }
}

function showResults() {
  resultsSection.classList.remove('hidden');
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Clears the form back to a blank single attendee row and hides any
// previous results — only called explicitly (the "New Meeting" button),
// never automatically after a successful calculation, so a user can tweak
// one value and recalculate without re-entering everything.
function resetForm() {
  meetingForm.reset();
  attendeesList.innerHTML = '';
  addAttendeeRow();
  recurringFieldsGroup.classList.add('hidden');
  resultsSection.classList.add('hidden');
  hideError();
  subjectInput.focus();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ========================================
// Form Submission
// ========================================

async function handleFormSubmit(e) {
  e.preventDefault();
  hideError();

  // Client-side validation
  if (!validateForm()) {
    showError('Validation Error', 'Please correct the errors above and try again.');
    return;
  }

  // Collect form data
  const meetingData = collectFormData();

  // Show loading
  showLoading();

  try {
    // Calculate cost
    const costResultData = await calculateCost(meetingData);
    displayCostResult(costResultData);
    showResults();

    // Get recommendations (non-blocking - always display cost even if this fails)
    const recommendationsData = await getRecommendations({
      ...meetingData,
      total_cost: costResultData.total_cost,
    });
    displayRecommendations(recommendationsData, costResultData.total_cost);

    // Deliberately NOT resetting the form here — the user can see their
    // results while their inputs stay exactly as entered, in case they want
    // to tweak one value and recalculate. Use the "New Meeting" button
    // (resetForm()) to start over explicitly.
  } catch (error) {
    showError('Error', error.message || 'An unexpected error occurred.');
  } finally {
    hideLoading();
  }
}
