import type { Playbook } from '../lib/api'

export function exportPlaybookMarkdown(playbook: Playbook): void {
  const lines: string[] = [
    '# Market Entry Playbook',
    '',
    `**Route:** ${playbook.origin_country} → ${playbook.target_country.name}`,
    `**Industry:** ${playbook.industry.name}`,
    playbook.company_description ? `**Company:** ${playbook.company_description}` : '',
    playbook.estimated_timeline_weeks
      ? `**Estimated timeline:** ${playbook.estimated_timeline_weeks} weeks`
      : '',
    `**Generated:** ${new Date(playbook.generated_at).toLocaleString()}`,
    '',
    '## Checklist',
    '',
  ]

  for (const step of playbook.steps) {
    const mark = step.is_completed ? 'x' : ' '
    lines.push(`- [${mark}] **${step.title}** (${step.step_type})`)
    lines.push(`  ${step.description}`)
    if (step.source_url) {
      lines.push(`  Source: ${step.source_url}`)
    }
    lines.push('')
  }

  const completed = playbook.steps.filter((s) => s.is_completed).length
  lines.push(`---`, `Progress: ${completed}/${playbook.steps.length} steps complete`)

  const blob = new Blob([lines.filter(Boolean).join('\n')], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `eastbridge-playbook-${playbook.target_country.code}-${playbook.id}.md`
  anchor.click()
  URL.revokeObjectURL(url)
}
