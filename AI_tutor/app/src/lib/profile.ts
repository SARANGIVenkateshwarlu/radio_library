/** Device-bound learner identity (anonymous, no sign-in needed). */
export function getDeviceToken(): string {
  const KEY = "real-ai-tutor.device-token";
  let t = localStorage.getItem(KEY);
  if (!t) {
    t = crypto.randomUUID().replace(/-/g, "");
    localStorage.setItem(KEY, t);
  }
  return t;
}
