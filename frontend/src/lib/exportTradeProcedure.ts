import type { TradeProcedure } from './api'

export function tradeProcedureToMarkdown(proc: TradeProcedure): string {
  const lines: string[] = [
    '# EAC Trade Procedure',
    '',
    `**${proc.title}**`,
    `**Country:** ${proc.country.name} (${proc.country.code})`,
    `**Activity:** ${proc.activity_type}`,
    `**Source:** ${proc.source_portal}`,
    proc.estimated_days ? `**Estimated duration:** ${proc.estimated_days} days` : '',
    proc.estimated_cost ? `**Estimated cost:** ${proc.estimated_cost}` : '',
    `**Last synced:** ${new Date(proc.last_synced_at).toLocaleString()}`,
    '',
    proc.summary,
    '',
    '## Steps',
    '',
  ]

  for (const [i, step] of proc.steps.entries()) {
    lines.push(`### ${i + 1}. ${step.title}`)
    if (step.responsible_agency) {
      lines.push(`**Agency:** ${step.responsible_agency}`)
    }
    if (step.estimated_days) {
      lines.push(`**Estimated:** ${step.estimated_days} days`)
    }
    lines.push('', step.description, '')
    if (step.documents_required.length > 0) {
      lines.push('**Documents required:**')
      for (const doc of step.documents_required) {
        lines.push(`- ${doc}`)
      }
      lines.push('')
    }
  }

  lines.push('---', `[Official source](${proc.source_url})`)
  return lines.filter((line) => line !== '').join('\n')
}

export function exportTradeProcedureMarkdown(proc: TradeProcedure): void {
  const blob = new Blob([tradeProcedureToMarkdown(proc)], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `eastbridge-trade-${proc.country.code}-${proc.slug || proc.id}.md`
  anchor.click()
  URL.revokeObjectURL(url)
}
