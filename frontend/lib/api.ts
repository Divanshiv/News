export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function errorMessage(response: Response): Promise<string> {
  const fallback = `Backend request failed: ${response.status} ${response.statusText}`;
  try {
    const body = (await response.json()) as unknown;
    if (
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof (body as { detail: unknown }).detail === "string"
    ) {
      return (body as { detail: string }).detail;
    }
  } catch {
    // Response body is not JSON — fall back to the status line.
  }
  return fallback;
}

export async function apiGet<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(
      `Unable to reach the backend at ${API_BASE}${path}. Is it running?`,
      { cause: error },
    );
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }

  return (await response.json()) as T;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(
      `Unable to reach the backend at ${API_BASE}${path}. Is it running?`,
      { cause: error },
    );
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }

  return (await response.json()) as T;
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(
      `Unable to reach the backend at ${API_BASE}${path}. Is it running?`,
      { cause: error },
    );
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }

  return (await response.json()) as T;
}

export async function apiDelete<T = void>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(
      `Unable to reach the backend at ${API_BASE}${path}. Is it running?`,
      { cause: error },
    );
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}