import { useQuery } from '@tanstack/react-query'
import { feedbackApi } from '../lib/api'
import { formatDate } from '../lib/utils'

type FeedbackItem = {
  id: string
  data_source_id: string
  raw_content: string
  clean_content: string | null
  author_handle: string | null
  posted_at: string | null
  url: string | null
  created_at: string
}

export default function Feedback() {
  const { data: feedbackData, isLoading } = useQuery({
    queryKey: ['feedback'],
    queryFn: async () => {
      const response = await feedbackApi.list()
      return response.data as FeedbackItem[]
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Raw Feedback</h1>
        <p className="mt-2 text-gray-600">
          View crawled feedback data before insight extraction
        </p>
      </div>

      <div className="bg-white shadow rounded-lg">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Content
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Author
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Posted
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Crawled
                </th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-6 text-center text-gray-500">
                    Loading feedback…
                  </td>
                </tr>
              ) : !feedbackData || feedbackData.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-6 text-center text-gray-500">
                    No feedback data yet. Run a crawl to collect data.
                  </td>
                </tr>
              ) : (
                feedbackData.map((item) => (
                  <tr key={item.id}>
                    <td className="px-6 py-4">
                      <div className="max-w-md">
                        <p className="text-sm text-gray-900 line-clamp-3">
                          {item.clean_content || item.raw_content}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {item.author_handle || '—'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {formatDate(item.posted_at)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {formatDate(item.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right text-sm">
                      {item.url ? (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:text-primary/80"
                        >
                          View
                        </a>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
