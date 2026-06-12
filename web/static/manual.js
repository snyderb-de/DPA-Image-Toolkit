'use strict';

const THEME_KEY = 'dpa-toolkit-theme';

document.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem(THEME_KEY) || 'dark';
  applyTheme(saved, false);
});

function setTheme(theme) {
  applyTheme(theme, true);
}

function applyTheme(theme, save) {
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('theme-dark').classList.toggle('active', theme === 'dark');
  document.getElementById('theme-light').classList.toggle('active', theme === 'light');
  if (save) localStorage.setItem(THEME_KEY, theme);
}
