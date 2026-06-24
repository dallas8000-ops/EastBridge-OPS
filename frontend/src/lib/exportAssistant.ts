import type { AssistantResponse } from './api'

export function assistantToMarkdown(response: AssistantResponse): string {
  const lines: string[] = [
    '# EastBridge Assistant Answer',
    '',
    `**Question:** ${response.question}`,
    `**Generated:** ${new Date(response.created_at).toLocaleString()}`,
  ]
  if (response.retrieval_method) {
    lines.push(`**Retrieval:** ${response.retrieval_method}`)
  }
  lines.push('')

  if (!response.has_sufficient_evidence) {
    lines.push('## Insufficient evidence', '', response.refusal_reason || 'No matching sources found.')
    return lines.join('\n')
  }

  lines.push('## Answer', '', response.answer || '', '', '## Citations', '')
  for (const [i, citation] of response.citations.entries()) {
    lines.push(
      `${i + 1}. [${citation.evidence.title}](${citation.evidence.source_url})`,
      `   > ${citation.excerpt.replace(/\n/g, '\n   > ')}`,
      '',
    )
  }
  return lines.join('\n')
}

export function exportAssistantMarkdown(response: AssistantResponse): void {
  const blob = new Blob([assistantToMarkdown(response)], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `eastbridge-answer-${response.id}.md`
  anchor.click()
  URL.revokeObjectURL(url)
}

export async function copyAssistantMarkdown(response: AssistantResponse): Promise<void> {
  await navigator.clipboard.writeText(assistantToMarkdown(response))
}
