export function assistantLink(question: string, countryCode?: string): string {
  const params = new URLSearchParams()
  params.set('q', question)
  if (countryCode) params.set('country', countryCode.toUpperCase())
  return `/assistant?${params.toString()}`
}
