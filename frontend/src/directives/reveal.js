// v-reveal: fade and lift an element 8 px the first time it scrolls into view.
// The optional value is a delay in ms, for staggering siblings: v-reveal="i * 30".
// Styles are in assets/motion.css. One observer is shared by every element.

const observer = 'IntersectionObserver' in window
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        entry.target.classList.add('is-visible')
        observer.unobserve(entry.target)
      }
    }, { rootMargin: '0px 0px -5% 0px' })
  : null

export default {
  mounted(el, { value }) {
    if (value) el.style.setProperty('--reveal-delay', `${value}ms`)
    el.classList.add('reveal')
    if (observer) observer.observe(el)
    else el.classList.add('is-visible')
  },
  unmounted(el) {
    observer?.unobserve(el)
  },
}
