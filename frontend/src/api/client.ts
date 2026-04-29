import { clearAuth } from '../composables/useAuth'

export class HttpError extends Error {
  status: number
  detail?: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.name = 'HttpError'
    this.status = status
    this.detail = detail
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: BodyInit | object | null
}

function buildHeaders(headers?: HeadersInit, hasJsonBody?: boolean): Headers {
  const finalHeaders = new Headers(headers)

  if (hasJsonBody && !finalHeaders.has('Content-Type')) {
    finalHeaders.set('Content-Type', 'application/json')
  }

  return finalHeaders
}

async function parseError(response: Response): Promise<never> {
  let detail: unknown = undefined
  let message = response.statusText

  try {
    const json = (await response.json()) as { detail?: unknown }
    detail = json.detail
    if (typeof json.detail === 'string') {
      message = json.detail
    }
  } catch {
    // Ignore parse failures and fall back to status text.
  }

  throw new HttpError(response.status, message, detail)
}

async function request<T>(
  url: string,
  options: RequestOptions = {},
): Promise<T> {
  const isJsonBody =
    options.body !== undefined &&
    options.body !== null &&
    typeof options.body === 'object' &&
    !(options.body instanceof FormData) &&
    !(options.body instanceof URLSearchParams)

  let requestBody: BodyInit | undefined
  if (isJsonBody) {
    requestBody = JSON.stringify(options.body)
  } else if (options.body !== undefined && options.body !== null) {
    requestBody = options.body as BodyInit
  }

  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: buildHeaders(options.headers, isJsonBody),
    body: requestBody,
  })

  if (!response.ok) {
    if (response.status === 401 && !window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/auth')) {
      clearAuth()
      const redirect = window.location.pathname + window.location.search
      window.location.href = `/login?redirect=${encodeURIComponent(redirect)}`
    }
    return parseError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const apiClient = {
  get<T>(url: string, options?: RequestOptions) {
    return request<T>(url, { ...options, method: 'GET' })
  },
  post<T>(
    url: string,
    body?: RequestOptions['body'],
    options?: RequestOptions,
  ) {
    return request<T>(url, { ...options, method: 'POST', body })
  },
  put<T>(url: string, body?: RequestOptions['body'], options?: RequestOptions) {
    return request<T>(url, { ...options, method: 'PUT', body })
  },
  patch<T>(
    url: string,
    body?: RequestOptions['body'],
    options?: RequestOptions,
  ) {
    return request<T>(url, { ...options, method: 'PATCH', body })
  },
  delete<T>(url: string, options?: RequestOptions) {
    return request<T>(url, { ...options, method: 'DELETE' })
  },
}
