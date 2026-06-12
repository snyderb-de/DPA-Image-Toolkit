'use strict';

const THEME_KEY = 'dpa-toolkit-theme';
const NAMED_KEY = 'dpa-toolkit-named-theme';

document.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem(THEME_KEY) || 'dark';
  const named = localStorage.getItem(NAMED_KEY) || '';
  applyTheme(saved, false);
  applyNamedTheme(named, false);
});

function setTheme(theme) {
  applyTheme(theme, true);
  applyNamedTheme('', true);
}

function setNamedTheme(name) {
  applyNamedTheme(name, true);
  if (name) applyTheme('dark', false);
}

function applyTheme(theme, save) {
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('theme-dark').classList.toggle('active', theme === 'dark');
  document.getElementById('theme-light').classList.toggle('active', theme === 'light');
  if (save) localStorage.setItem(THEME_KEY, theme);
}

function applyNamedTheme(name, save) {
  document.documentElement.setAttribute('data-named-theme', name);
  document.querySelectorAll('.named-theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.trim().toLowerCase().startsWith(name.split('-')[0]));
  });
  if (save) localStorage.setItem(NAMED_KEY, name);
}
