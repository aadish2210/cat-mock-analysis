export function formatNumber(value, suffix = '') {
  const number = Number(value || 0)
  return `${Number.isInteger(number) ? number : number.toFixed(1)}${suffix}`
}