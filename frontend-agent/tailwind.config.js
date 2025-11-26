/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                slate: {
                    900: '#0F172A', // Dark background
                    800: '#1E293B', // Sidebar/Cards
                }
            }
        },
    },
    plugins: [],
}
