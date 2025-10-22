import { useQuery } from '@tanstack/react-query'
import { MessageSquare, TrendingUp, Database, AlertCircle } from 'lucide-react'
import { statsApi } from '../lib/api'
import MetricCard from '../components/MetricCard'
import SentimentBadge from '../components/SentimentBadge'

export default function Dashboard() {
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: async () => {
      const response = await statsApi.overview()
      return response.data
    },
  })

  const { data: recentData, isLoading: recentLoading } = useQuery({
    queryKey: ['stats', 'recent-insights'],
    queryFn: async () => {
      const response = await statsApi.recentInsights(5)
      return response.data
    },
  })

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">Overview of your Voice of Customer insights</p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Total Insights"
          value={overview?.total_insights ?? '-'}
          icon={MessageSquare}
          loading={overviewLoading}
        />
        <MetricCard
          title="Avg Sentiment"
          value={overview?.avg_sentiment ? `${overview.avg_sentiment > 0 ? '+' : ''}${overview.avg_sentiment}` : '-'}
          icon={TrendingUp}
          loading={overviewLoading}
        />
        <MetricCard
          title="Active Sources"
          value={overview?.active_sources ?? '-'}
          icon={Database}
          loading={overviewLoading}
        />
        <MetricCard
          title="Open Alerts"
          value={overview?.open_alerts ?? '-'}
          icon={AlertCircle}
          loading={overviewLoading}
        />
      </div>

      {/* Sentiment Breakdown */}
      {overview?.sentiment_breakdown && (
        <div className="bg-white p-6 rounded-lg shadow mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Sentiment Distribution</h2>
          <div className="flex gap-4">
            {Object.entries(overview.sentiment_breakdown).map(([label, count]) => (
              <div key={label} className="flex items-center gap-2">
                <SentimentBadge label={label} />
                <span className="text-sm text-gray-600">{count as number}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Insights */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Insights</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {recentLoading ? (
            <div className="p-6 text-center text-gray-500">Loading...</div>
          ) : recentData?.insights?.length > 0 ? (
            recentData.insights.map((insight: any) => (
              <div key={insight.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">{insight.summary}</p>
                    <div className="mt-2 flex items-center gap-3">
                      <SentimentBadge
                        label={insight.sentiment_label}
                        score={insight.sentiment_score}
                      />
                      {insight.urgency_level && (
                        <span className="text-xs text-gray-500">
                          Urgency: {insight.urgency_level}
                        </span>
                      )}
                      <span className="text-xs text-gray-500">
                        {new Date(insight.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-gray-500">No recent insights</div>
          )}
        </div>
      </div>
    </div>
  )
}
