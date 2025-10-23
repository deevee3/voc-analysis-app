import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { crawlsApi, sourcesApi } from '../lib/api'
import { capitalize, formatDate } from '../lib/utils'

type DataSource = {
  id: string
  name: string
  platform: string
  config: Record<string, unknown>
  is_active: boolean
  schedule: string | null
  last_crawl_at: string | null
  created_at: string
  updated_at: string | null
}

type CrawlTriggerPayload = {
  data_source_id: string
  query_override?: Record<string, string>
}

type FormState = {
  id?: string
  name: string
  platform: string
  configText: string
  schedule: string
  isActive: boolean
  error?: string
}

const PLATFORM_OPTIONS = ['reddit', 'twitter', 'youtube', 'trustpilot', 'quora', 'g2']

export default function Sources() {
  const queryClient = useQueryClient()
  const [isEditorOpen, setEditorOpen] = useState(false)
  const [formState, setFormState] = useState<FormState | null>(null)
  const [activeCrawlId, setActiveCrawlId] = useState<string | null>(null)
  const [crawlError, setCrawlError] = useState<{ sourceId: string; message: string } | null>(null)

  const sourcesQuery = useQuery({
    queryKey: ['sources'],
    queryFn: async () => {
      const response = await sourcesApi.list()
      return response.data as DataSource[]
    },
    staleTime: 30_000,
  })

  const createMutation = useMutation({
    mutationFn: async (payload: Omit<FormState, 'id' | 'error'>) => {
      const config = parseConfig(payload.configText)
      return sourcesApi.create({
        name: payload.name,
        platform: payload.platform,
        config,
        is_active: payload.isActive,
        schedule: payload.schedule || null,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      closeEditor()
    },
    onError: (error: unknown) => {
      setFormState((previous) =>
        previous
          ? {
              ...previous,
              error: extractErrorMessage(error),
            }
          : previous
      )
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (payload: FormState) => {
      if (!payload.id) {
        throw new Error('Missing id for update')
      }
      const config = parseConfig(payload.configText)
      return sourcesApi.update(payload.id, {
        name: payload.name,
        is_active: payload.isActive,
        config,
        schedule: payload.schedule || null,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      closeEditor()
    },
    onError: (error: unknown) => {
      setFormState((previous) =>
        previous
          ? {
              ...previous,
              error: extractErrorMessage(error),
            }
          : previous
      )
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => sourcesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })

  const crawlMutation = useMutation({
    mutationFn: async (payload: CrawlTriggerPayload) => {
      await crawlsApi.trigger(payload)
    },
    onMutate: (variables) => {
      setActiveCrawlId(variables.data_source_id)
      setCrawlError(null)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      setCrawlError(null)
    },
    onError: (error: unknown, variables) => {
      setCrawlError({
        sourceId: variables.data_source_id,
        message: extractErrorMessage(error),
      })
    },
    onSettled: () => {
      setActiveCrawlId(null)
    },
  })

  const sortedSources = useMemo(() => {
    if (!sourcesQuery.data) {
      return []
    }
    return [...sourcesQuery.data].sort((a, b) => b.created_at.localeCompare(a.created_at))
  }, [sourcesQuery.data])

  const isSaving = createMutation.isPending || updateMutation.isPending

  function openCreateEditor() {
    setFormState({
      name: '',
      platform: PLATFORM_OPTIONS[0],
      configText: '{\n  "query": ""\n}',
      schedule: '',
      isActive: true,
    })
    setEditorOpen(true)
  }

  function openEditEditor(source: DataSource) {
    setFormState({
      id: source.id,
      name: source.name,
      platform: source.platform,
      configText: JSON.stringify(source.config ?? {}, null, 2),
      schedule: source.schedule ?? '',
      isActive: source.is_active,
    })
    setEditorOpen(true)
  }

  function closeEditor() {
    setEditorOpen(false)
    setFormState(null)
    createMutation.reset()
    updateMutation.reset()
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!formState) {
      return
    }

    try {
      parseConfig(formState.configText)
    } catch (error) {
      setFormState({ ...formState, error: extractErrorMessage(error) })
      return
    }

    if (formState.id) {
      updateMutation.mutate(formState)
    } else {
      createMutation.mutate(formState)
    }
  }

  function handleDelete(id: string) {
    if (deleteMutation.isPending) {
      return
    }
    deleteMutation.mutate(id)
  }

  function handleTriggerCrawl(source: DataSource) {
    if (activeCrawlId) {
      return
    }

    const payload: CrawlTriggerPayload = {
      data_source_id: source.id,
    }

    const config = source.config ?? {}
    const query = typeof config.query === 'string' ? config.query : undefined
    const subreddit = typeof config.subreddit === 'string' ? config.subreddit : undefined

    if (query || subreddit) {
      payload.query_override = {}
      if (query) {
        payload.query_override.query = query
      }
      if (subreddit) {
        payload.query_override.subreddit = subreddit
      }
    }

    crawlMutation.mutate(payload)
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Data Sources</h1>
            <p className="mt-2 text-gray-600">
              Configure crawler endpoints that will feed live customer feedback into the pipeline.
            </p>
          </div>
          <button
            type="button"
            onClick={openCreateEditor}
            className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
          >
            Add source
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {crawlMutation.isError ? (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            {extractErrorMessage(crawlMutation.error)}
          </div>
        ) : null}

        <div className="bg-white shadow rounded-lg">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Platform
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Active
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Last crawl
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Schedule
                  </th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {sourcesQuery.isLoading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-6 text-center text-gray-500">
                      Loading sources…
                    </td>
                  </tr>
                ) : sortedSources.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-6 text-center text-gray-500">
                      No data sources configured yet.
                    </td>
                  </tr>
                ) : (
                  sortedSources.map((source) => (
                    <tr key={source.id}>
                      <td className="px-6 py-4">
                        <div className="font-medium text-gray-900">{source.name}</div>
                        <div className="text-sm text-gray-500">
                          {renderConfigSummary(source.config)}
                        </div>
                        {crawlError?.sourceId === source.id ? (
                          <div className="mt-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                            {crawlError.message}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{capitalize(source.platform)}</td>
                      <td className="px-6 py-4 text-sm">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            source.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                          }`}
                        >
                          {source.is_active ? 'Active' : 'Paused'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{formatDate(source.last_crawl_at)}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{source.schedule ?? '—'}</td>
                      <td className="px-6 py-4 text-right text-sm">
                        <div className="inline-flex gap-2">
                          <button
                            type="button"
                            onClick={() => openEditEditor(source)}
                            className="rounded-md border border-gray-300 px-3 py-1 text-sm font-medium text-gray-700 hover:bg-gray-50"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => handleTriggerCrawl(source)}
                            className="rounded-md border border-primary/40 px-3 py-1 text-sm font-medium text-primary hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-70"
                            disabled={activeCrawlId === source.id}
                          >
                            {activeCrawlId === source.id ? 'Running…' : 'Run crawl'}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(source.id)}
                            className="rounded-md border border-red-200 px-3 py-1 text-sm font-medium text-red-600 hover:bg-red-50"
                            disabled={deleteMutation.isPending}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {isEditorOpen && formState ? (
        <div className="fixed inset-0 z-10 flex items-center justify-center bg-gray-900/50 px-4">
          <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
            <div className="flex items-start justify-between border-b border-gray-200 px-6 py-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {formState.id ? 'Edit data source' : 'Create data source'}
                </h2>
                <p className="text-sm text-gray-500">
                  Provide crawler configuration. Config accepts JSON values like subreddit or query keywords.
                </p>
              </div>
              <button
                type="button"
                onClick={closeEditor}
                className="rounded-md p-1 text-gray-400 hover:text-gray-500"
              >
                <span className="sr-only">Close</span>
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 px-6 py-6">
              {formState.error ? (
                <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                  {formState.error}
                </div>
              ) : null}

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Name</label>
                  <input
                    type="text"
                    value={formState.name}
                    onChange={(event) => setFormState({ ...formState, name: event.target.value })}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Platform</label>
                  <select
                    value={formState.platform}
                    onChange={(event) => setFormState({ ...formState, platform: event.target.value })}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    disabled={Boolean(formState.id)}
                  >
                    {PLATFORM_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {capitalize(option)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Crawler config (JSON)</label>
                <textarea
                  value={formState.configText}
                  onChange={(event) => setFormState({ ...formState, configText: event.target.value })}
                  rows={6}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  spellCheck={false}
                  required
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Schedule (optional)</label>
                  <input
                    type="text"
                    value={formState.schedule}
                    onChange={(event) => setFormState({ ...formState, schedule: event.target.value })}
                    placeholder="e.g. every 30m"
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <input
                    id="is-active-toggle"
                    type="checkbox"
                    checked={formState.isActive}
                    onChange={(event) => setFormState({ ...formState, isActive: event.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                  />
                  <label htmlFor="is-active-toggle" className="text-sm font-medium text-gray-700">
                    Active
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeEditor}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isSaving ? 'Saving…' : 'Save source'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function parseConfig(configText: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(configText || '{}')
    if (typeof parsed !== 'object' || parsed === null) {
      throw new Error('Config must be a JSON object')
    }
    return parsed as Record<string, unknown>
  } catch (error) {
    throw new Error(extractErrorMessage(error) || 'Invalid JSON configuration')
  }
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  if (typeof error === 'string') {
    return error
  }
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as any).response?.data?.detail === 'string'
  ) {
    return (error as any).response.data.detail
  }
  return 'An unexpected error occurred'
}

function renderConfigSummary(config: Record<string, unknown> | undefined): string {
  if (!config || Object.keys(config).length === 0) {
    return 'No config provided'
  }

  const [firstKey] = Object.keys(config)
  if (!firstKey) {
    return 'No config provided'
  }

  const value = config[firstKey]
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return `${firstKey}: ${value}`
  }

  return `${firstKey}: …`
}
