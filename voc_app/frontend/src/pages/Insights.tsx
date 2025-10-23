import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { statsApi, insightsApi } from '../lib/api'
import SentimentBadge from '../components/SentimentBadge'

enum DrawerState {
  Closed,
  Loading,
  Loaded,
}

type SentimentFilter = 'all' | 'positive' | 'neutral' | 'negative'

export default function Insights() {
  const [keyword, setKeyword] = useState('')
  const [sentiment, setSentiment] = useState<SentimentFilter>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [drawerState, setDrawerState] = useState<DrawerState>(DrawerState.Closed)

  const filters = useMemo(() => {
    const params: Record<string, string> = {}
    if (keyword.trim().length >= 2) {
      params.keyword = keyword.trim()
    }
    if (sentiment !== 'all') {
      params.sentiment_label = sentiment
    }
    return params
  }, [keyword, sentiment])

  const { data: insightsData, isLoading } = useQuery({
    queryKey: ['insights', filters],
    queryFn: async () => {
      const response = await insightsApi.list(filters)
      return response.data as InsightListItem[]
    },
  })

  const { data: overview } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: async () => {
      const response = await statsApi.overview()
      return response.data
    },
  })

  const detailQuery = useQuery<InsightDetail | null>({
    queryKey: ['insight', selectedId],
    queryFn: async () => {
      if (!selectedId) {
        return null
      }
      const response = await insightsApi.get(selectedId)
      return response.data as InsightDetail
    },
    enabled: drawerState !== DrawerState.Closed && !!selectedId,
    staleTime: 30_000,
    retry: 1,
  })

  useEffect(() => {
    if (detailQuery.status === 'success' && drawerState === DrawerState.Loading) {
      setDrawerState(DrawerState.Loaded)
    }
  }, [detailQuery.status, drawerState])

  return (
    <div className="relative">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Insights</h1>
        <p className="mt-2 text-gray-600">Search and analyze extracted customer insights</p>
      </div>

      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">Keyword</label>
              <input
                type="text"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                placeholder="Search summaries"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              />
              <p className="mt-1 text-xs text-gray-400">Minimum 2 characters</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Sentiment</label>
              <select
                value={sentiment}
                onChange={(event) => setSentiment(event.target.value as SentimentFilter)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              >
                <option value="all">All sentiments</option>
                <option value="positive">Positive</option>
                <option value="neutral">Neutral</option>
                <option value="negative">Negative</option>
              </select>
            </div>
            <div className="flex items-end">
              <div className="text-sm text-gray-500">
                <p>Total insights: {overview?.total_insights ?? '-'}</p>
                <p>Open alerts: {overview?.open_alerts ?? '-'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Results</h2>
          <span className="text-sm text-gray-500">
            Showing {insightsData?.length ?? 0} of {overview?.total_insights ?? 0}
          </span>
        </div>
        <div className="divide-y divide-gray-200">
          {isLoading ? (
            <div className="p-6 text-center text-gray-500">Loading insights…</div>
          ) : insightsData && insightsData.length > 0 ? (
            insightsData.map((insight) => (
              <InsightRow
                key={insight.id}
                insight={insight}
                onSelect={() => {
                  setSelectedId(insight.id)
                  setDrawerState(DrawerState.Loading)
                }}
              />
            ))
          ) : (
            <div className="p-6 text-center text-gray-500">No insights match the current filters.</div>
          )}
        </div>
      </div>

      <InsightDrawer
        state={drawerState}
        onClose={() => {
          setDrawerState(DrawerState.Closed)
          setSelectedId(null)
        }}
        isLoading={detailQuery.isFetching && drawerState !== DrawerState.Closed}
        insight={detailQuery.data}
      />
    </div>
  )
}

interface InsightListItem {
  id: string
  feedback_id: string
  sentiment_score: number | null
  sentiment_label: string | null
  summary: string
  journey_stage: string | null
  urgency_level: number | null
  created_at: string
}

interface InsightDetail extends InsightListItem {
  pain_points: Record<string, string>[] | null
  feature_requests: Record<string, string>[] | null
  competitor_mentions: Record<string, string>[] | null
  customer_context: Record<string, string> | null
}

function InsightRow({ insight, onSelect }: { insight: InsightListItem; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full text-left p-6 hover:bg-gray-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 pr-6">
          <p className="text-sm text-gray-900">{insight.summary}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
            <SentimentBadge label={insight.sentiment_label} score={insight.sentiment_score} />
            {insight.journey_stage && <span>Journey: {insight.journey_stage}</span>}
            {insight.urgency_level !== null && <span>Urgency: {insight.urgency_level}</span>}
            <span>{new Date(insight.created_at).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </button>
  )
}

function InsightDrawer({
  state,
  insight,
  isLoading,
  onClose,
}: {
  state: DrawerState
  insight: InsightDetail | null | undefined
  isLoading: boolean
  onClose: () => void
}) {
  const isOpen = state !== DrawerState.Closed

  return (
    <div
      className={`fixed inset-y-0 right-0 z-40 w-full max-w-xl transform bg-white shadow-xl transition-transform duration-200 ease-in-out ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
      role="dialog"
      aria-modal={isOpen}
    >
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Insight Details</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close insight details"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {isLoading || state === DrawerState.Loading ? (
            <p className="text-sm text-gray-500">Loading insight details…</p>
          ) : insight ? (
            <div className="space-y-6">
              <section>
                <h3 className="text-sm font-semibold text-gray-700">Summary</h3>
                <p className="mt-2 text-sm text-gray-900">{insight.summary}</p>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-gray-700">Sentiment & Context</h3>
                <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                  <SentimentBadge label={insight.sentiment_label} score={insight.sentiment_score} />
                  {insight.journey_stage && <span>Journey: {insight.journey_stage}</span>}
                  {insight.urgency_level !== null && <span>Urgency: {insight.urgency_level}</span>}
                  <span>Created: {new Date(insight.created_at).toLocaleString()}</span>
                </div>
              </section>

              <DetailList title="Pain Points" items={insight.pain_points} empty="No pain points captured" />
              <DetailList
                title="Feature Requests"
                items={insight.feature_requests}
                empty="No feature requests captured"
              />
              <DetailList
                title="Competitor Mentions"
                items={insight.competitor_mentions}
                empty="No competitor mentions"
              />
              <section>
                <h3 className="text-sm font-semibold text-gray-700">Customer Context</h3>
                {insight.customer_context ? (
                  <ul className="mt-2 space-y-1 text-sm text-gray-600">
                    {Object.entries(insight.customer_context).map(([key, value]) => (
                      <li key={key}>
                        <span className="font-medium text-gray-700">{key}:</span> {value}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-gray-500">No customer context provided.</p>
                )}
              </section>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Select an insight to view details.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function DetailList({
  title,
  items,
  empty,
}: {
  title: string
  items: Record<string, string>[] | null
  empty: string
}) {
  if (!items || items.length === 0) {
    return (
      <section>
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        <p className="mt-2 text-sm text-gray-500">{empty}</p>
      </section>
    )
  }

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      <ul className="mt-2 space-y-2">
        {items.map((item, index) => (
          <li key={`${title}-${index}`} className="rounded-md bg-gray-50 p-3 text-sm text-gray-700">
            <ul className="space-y-1">
              {Object.entries(item).map(([key, value]) => (
                <li key={key}>
                  <span className="font-medium text-gray-800">{key}:</span> {value}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  )
}
