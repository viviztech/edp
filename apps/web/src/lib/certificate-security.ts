const code = "[A-Za-z0-9_-]{20,48}";

export function certificatePath(path: string[], method: string): string | null {
  if (method !== "GET") return null;
  const value = path.join("/");
  return new RegExp(`^verify/${code}(/qr)?$`).test(value)
    ? `/certificates/${value}`
    : null;
}
