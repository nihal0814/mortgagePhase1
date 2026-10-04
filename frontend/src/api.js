import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export const getApplications = (params = {}) => api.get("/applications", { params });
export const getApplication = (id) => api.get(`/applications/${id}`);
export const createApplication = (data) => api.post("/applications", data);
export const updateApplication = (id, data) => api.put(`/applications/${id}`, data);
export const updateStatus = (id, status) => api.patch(`/applications/${id}/status`, { status });
export const getDocuments = (applicationId) => api.get(`/applications/${applicationId}/documents`);
export const getDocument = (applicationId, documentId) => api.get(`/applications/${applicationId}/documents/${documentId}`);
export const uploadDocument = (applicationId, file, category, onUploadProgress) => {
  const data = new FormData();
  data.append("file", file);
  data.append("category", category);
  return api.post(`/applications/${applicationId}/documents`, data, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
};
export const updateDocumentCategory = (applicationId, documentId, category) =>
  api.put(`/applications/${applicationId}/documents/${documentId}`, { category });
export const deleteDocument = (applicationId, documentId) =>
  api.delete(`/applications/${applicationId}/documents/${documentId}`);
export const extractDocument = (applicationId, documentId) =>
  api.post(`/applications/${applicationId}/documents/${documentId}/extract`);
export const getDocumentText = (applicationId, documentId) =>
  api.get(`/applications/${applicationId}/documents/${documentId}/text`);
export const analyzeDocument = (applicationId, documentId) =>
  api.post(`/applications/${applicationId}/documents/${documentId}/analyze`);
export const getDocumentAnalysis = (applicationId, documentId) =>
  api.get(`/applications/${applicationId}/documents/${documentId}/analysis`);
export const analyzeApplication = (applicationId) =>
  api.post(`/applications/${applicationId}/analyze`);
export const getApplicationAnalysis = (applicationId) =>
  api.get(`/applications/${applicationId}/analysis`);
export const validateApplication = (applicationId) =>
  api.post(`/applications/${applicationId}/validate`);
export const recalculateValidation = (applicationId) =>
  api.post(`/applications/${applicationId}/validation/recalculate`);
export const getValidation = (applicationId) =>
  api.get(`/applications/${applicationId}/validation`);
export const getPolicies = () => api.get("/policies");
export const deletePolicy = (policyId) => api.delete(`/policies/${policyId}`);
export const uploadPolicy = (file, metadata) => {
  const data = new FormData();
  data.append("file", file);
  Object.entries(metadata).forEach(([key, value]) => data.append(key, value));
  return api.post("/policies", data, { headers: { "Content-Type": "multipart/form-data" } });
};
export const searchPolicies = (query, top_k = 5) => api.post("/policies/search", { query, top_k });
export const analyzeApplicationPolicy = (applicationId) =>
  api.post(`/applications/${applicationId}/policy-analysis`);
export const runUnderwriting = (applicationId) =>
  api.post(`/applications/${applicationId}/underwriting/run`);
export const getUnderwritingStatus = (applicationId) =>
  api.get(`/applications/${applicationId}/underwriting/status`);
export const getUnderwritingEvents = (applicationId) =>
  api.get(`/applications/${applicationId}/underwriting/events`);
export const getUnderwritingReport = (applicationId) =>
  api.get(`/applications/${applicationId}/underwriting/report`);
