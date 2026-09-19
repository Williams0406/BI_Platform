export function displayName(user) {
  if (!user) return "Usuario";
  return user.full_name || [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;
}

export function initials(user) {
  const name = displayName(user);
  const parts = name.split(/\s+/).filter(Boolean);

  if (!parts.length) return "U";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}
