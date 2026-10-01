export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatAspectRatio(ratio: number): string {
  // Check common real estate and photography ratios
  const tolerance = 0.05;
  if (Math.abs(ratio - 16 / 9) < tolerance) return "16:9";
  if (Math.abs(ratio - 4 / 3) < tolerance) return "4:3";
  if (Math.abs(ratio - 3 / 2) < tolerance) return "3:2";
  if (Math.abs(ratio - 1) < tolerance) return "1:1";
  if (Math.abs(ratio - 9 / 16) < tolerance) return "9:16 (Portrait)";
  if (Math.abs(ratio - 3 / 4) < tolerance) return "3:4 (Portrait)";
  return `${ratio.toFixed(2)}:1`;
}

export function extractLocalImageDimensions(
  file: File
): Promise<{ width: number; height: number; aspectRatio: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);

    img.onload = () => {
      const width = img.naturalWidth;
      const height = img.naturalHeight;
      const aspectRatio = height > 0 ? Number((width / height).toFixed(4)) : 1;
      URL.revokeObjectURL(objectUrl);
      resolve({ width, height, aspectRatio });
    };

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Failed to decode image in browser."));
    };

    img.src = objectUrl;
  });
}

export function generateClientId(): string {
  return "client_" + Math.random().toString(36).substring(2, 9);
}
