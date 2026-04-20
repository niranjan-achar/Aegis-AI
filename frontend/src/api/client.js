import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export async function safeRequest(request) {
  try {
    const response = await request();
    return { data: response.data, error: null };
  } catch (error) {
    if (error.response) {
      return { data: null, error: error.response.data?.detail ?? "Request failed." };
    }
    return { data: null, error: "Backend offline. Start the FastAPI server on port 8000." };
  }
}

export { API_BASE_URL };
export default client;
