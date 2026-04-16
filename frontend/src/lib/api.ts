const API_BASE = "http://127.0.0.1:8000";

export const api = {
  async get(endpoint: string) {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async post(endpoint: string, data: any) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async upload(endpoint: string, file: File) {
    const formData = new FormData();
    // Importante: No nosso backend, o parametro se chama 'file', não 'video'
    formData.append("file", file); 
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};