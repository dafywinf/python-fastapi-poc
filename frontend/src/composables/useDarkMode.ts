import { ref, watchEffect } from 'vue'

const dark = ref(localStorage.getItem('theme') === 'dark')

watchEffect(() => {
  document.documentElement.setAttribute('data-theme', dark.value ? 'dark' : 'light')
  localStorage.setItem('theme', dark.value ? 'dark' : 'light')
})

export function useDarkMode() {
  function toggle() {
    dark.value = !dark.value
  }

  return { dark, toggle }
}
