
import type { ForensicUploadRequest } from "@/types/forensic";

export async function uploadForensicCsv({
  file,
  token_address,
}: ForensicUploadRequest) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("token_address", token_address);

  const response = await fetch("/backend/api/investigations/upload", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(
      error?.detail ?? `Upload failed: HTTP ${response.status}`
    );
  }

  return response.json();
}
