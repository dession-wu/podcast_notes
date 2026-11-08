export function escapeHTML(text) {
  return String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

export function highlightHTML(text, keyword, transcript = false) {
  if (!keyword.trim()) return escapeHTML(text);
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'));
  const open = transcript ? '<mark class="transcript-mark">' : '<mark>';
  return parts.map((part, i) => i % 2 ? open + escapeHTML(part) + '</mark>' : escapeHTML(part)).join('');
}
