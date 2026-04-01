// DPA Image Toolkit Dashboard - Script

// Dashboard state (can be updated with data.json later)
const dashboardState = {
    currentPhase: 1,
    phases: [
        { id: 1, name: 'Setup & Repository Integration', progress: 0, status: 'pending' },
        { id: 2, name: 'Analysis & Architecture Design', progress: 0, status: 'pending' },
        { id: 3, name: 'GUI Development & Integration', progress: 0, status: 'pending' },
        { id: 4, name: 'Testing & Refinement', progress: 0, status: 'pending' },
        { id: 5, name: 'Documentation & Deployment', progress: 0, status: 'pending' }
    ],
    repositories: [
        { id: 1, url: '', status: 'Not provided', integration: 'Pending' },
        { id: 2, url: '', status: 'Not provided', integration: 'Pending' }
    ]
};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    updateDashboard();
    setLastUpdated();
    loadDataFromFile();
});

// Update dashboard display
function updateDashboard() {
    updatePhaseInfo();
    updateProgressBar();
    updateRepositories();
    updatePhasesTimeline();
}

// Update current phase information
function updatePhaseInfo() {
    const currentPhase = dashboardState.phases[dashboardState.currentPhase - 1];
    document.getElementById('currentPhase').textContent = `Phase ${currentPhase.id}: ${currentPhase.name}`;
    document.getElementById('phaseProgress').textContent = `${currentPhase.progress}%`;
}

// Update overall progress bar
function updateProgressBar() {
    const totalPhases = dashboardState.phases.length;
    const completedPhases = dashboardState.phases.filter(p => p.status === 'completed').length;
    const activePhases = dashboardState.phases.filter(p => p.status === 'active').length;

    const overallProgress = ((completedPhases + (activePhases * 0.5)) / totalPhases) * 100;
    const progressFill = document.getElementById('overallProgress');
    progressFill.style.width = overallProgress + '%';

    document.getElementById('progressText').textContent = `${Math.round(overallProgress)}% Complete`;
}

// Update repository status
function updateRepositories() {
    dashboardState.repositories.forEach((repo, index) => {
        const repoNum = index + 1;
        document.getElementById(`repo${repoNum}-url`).textContent = repo.url || 'Not provided';
        document.getElementById(`repo${repoNum}-status`).textContent = repo.status;
        document.getElementById(`repo${repoNum}-integration`).textContent = repo.integration;
    });
}

// Update phases timeline
function updatePhasesTimeline() {
    dashboardState.phases.forEach((phase) => {
        const phaseElement = document.getElementById(`phase-${phase.id}`);
        const statusElement = phaseElement.querySelector('.phase-status');

        // Update status badge
        statusElement.textContent = phase.status.charAt(0).toUpperCase() + phase.status.slice(1);
        statusElement.className = `phase-status ${phase.status}`;

        // Update phase item class
        phaseElement.classList.remove('pending', 'active', 'completed');
        phaseElement.classList.add(phase.status);
    });
}

// Set last updated timestamp
function setLastUpdated() {
    const now = new Date();
    const formattedDate = now.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    document.getElementById('lastUpdated').textContent = formattedDate;
}

// Load data from data.json (for future use)
function loadDataFromFile() {
    // Placeholder for loading from data.json
    // fetch('data.json')
    //     .then(response => response.json())
    //     .then(data => {
    //         Object.assign(dashboardState, data);
    //         updateDashboard();
    //     })
    //     .catch(error => console.log('data.json not found, using defaults'));
}

// Function to update a specific phase (callable from console or programmatically)
function updatePhase(phaseId, status, progress = 0) {
    const phase = dashboardState.phases.find(p => p.id === phaseId);
    if (phase) {
        phase.status = status;
        phase.progress = progress;
        updateDashboard();
    }
}

// Function to update repository information
function updateRepository(repoNum, url, status, integration) {
    if (dashboardState.repositories[repoNum - 1]) {
        dashboardState.repositories[repoNum - 1] = { id: repoNum, url, status, integration };
        updateRepositories();
    }
}

// Function to set current phase
function setCurrentPhase(phaseId) {
    dashboardState.currentPhase = phaseId;
    updatePhaseInfo();
}

// Expose functions globally for console/programmatic use
window.dashboardAPI = {
    updatePhase,
    updateRepository,
    setCurrentPhase,
    getState: () => dashboardState
};

console.log('Dashboard initialized. Use window.dashboardAPI to update dashboard state.');
