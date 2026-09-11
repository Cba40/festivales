export function truncateId(id: string, maxLength = 8): string {
  return id.length > maxLength ? `${id.slice(0, maxLength)}...` : id;
}