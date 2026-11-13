// The site soundtrack. This is the only file to edit to change the music.
//
// Each entry is a YouTube video, played in order and looped. videoId is the part after
// "v=" in a watch URL (https://www.youtube.com/watch?v=VIDEO_ID). Optional `start` is the
// second to begin from, to skip an intro.
//
// Before adding a video, check its owner allows embedding: open
//   https://www.youtube-nocookie.com/embed/VIDEO_ID
// in a private window. If it plays there, it will play here. "Video unavailable" means
// embedding is disabled, and the player will skip that entry.

export const tracks = [
  { videoId: 'dpvQqmX6SUI', title: 'Just Keep Watching', artist: 'Tate McRae', start: 3 },
]
