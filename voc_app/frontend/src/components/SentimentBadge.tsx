interface SentimentBadgeProps {
  label: string | null
  score?: number | null
}

export default function SentimentBadge({ label, score }: SentimentBadgeProps) {
  if (!label) return null

  const colors = {
    positive: 'bg-green-100 text-green-800',
    neutral: 'bg-gray-100 text-gray-800',
    negative: 'bg-red-100 text-red-800',
  }

  const colorClass = colors[label as keyof typeof colors] || colors.neutral

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {label}
      {score !== null && score !== undefined && (
        <span className="ml-1">({score > 0 ? '+' : ''}{score.toFixed(2)})</span>
      )}
    </span>
  )
}
