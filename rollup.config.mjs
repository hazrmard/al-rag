import svelte from 'rollup-plugin-svelte';
import commonjs from '@rollup/plugin-commonjs';
import resolve from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';
import css from 'rollup-plugin-css-only';
import replace from '@rollup/plugin-replace';
import copy from 'rollup-plugin-copy';
import 'dotenv/config';

const production = process.env.PROD;
const apiPort = process.env.QURANAI_API_PORT || '7999';
const apiBaseUrl = production ? process.env.QURANAI_API_BASE_URL : `http://localhost:${apiPort}`;

console.log(`Building for ${production ? 'production' : 'development'}...`);
console.log(`API_BASE_URL: ${apiBaseUrl}`);

export default [
  // Bundle for Extension
  {
    input: 'src/frontend/extension/index.js',
    output: {
      sourcemap: true,
      format: 'iife',
      name: 'app',
      file: 'public/extension/bundle.js'
    },
    plugins: [
      replace({
        preventAssignment: true,
        values: {
          '__QURANAI_API_BASE_URL__': JSON.stringify(apiBaseUrl),
          '__QURANAI_IS_EXTENSION__': JSON.stringify(true)
        }
      }),
      svelte({
        compilerOptions: {
          // enable run-time checks when not in production
          dev: !production
        }
      }),
      // we'll extract any component CSS out into
      // a separate file - better for performance
      css({ output: 'bundle.css' }),

      // If you have external dependencies installed from
      // npm, you'll most likely need these plugins. In
      // some cases you'll need additional configuration -
      // consult the documentation for details:
      // https://github.com/rollup/plugins/tree/master/packages/commonjs
      resolve({
        browser: true,
        dedupe: ['svelte']
      }),
      commonjs(),

      copy({
        targets: [
          { src: 'src/frontend/extension/index.html', dest: 'public/extension' },
          { src: 'src/frontend/extension/manifest.json', dest: 'public/extension' },
          { src: 'src/frontend/extension/background.js', dest: 'public/extension' },
          { src: 'src/frontend/extension/content.js', dest: 'public/extension' },
          { src: 'src/frontend/extension/main.png', dest: 'public/extension' }
        ],
        verbose: true
      }),

      // If we're building for production (npm run build
      // instead of npm run dev), minify
      production && terser()
    ],
    watch: {
      clearScreen: false
    }
  },
  // Bundle for Standalone Web App
  {
    input: 'src/frontend/app/index.js',
    output: {
      sourcemap: true,
      format: 'iife',
      name: 'app',
      file: 'public/app/bundle.js'
    },
    plugins: [
      replace({
        preventAssignment: true,
        values: {
          '__QURANAI_API_BASE_URL__': JSON.stringify(apiBaseUrl),
          '__QURANAI_IS_EXTENSION__': JSON.stringify(false)
        }
      }),
      svelte({
        compilerOptions: {
          dev: !production
        }
      }),
      css({ output: 'bundle.css' }),
      resolve({
        browser: true,
        dedupe: ['svelte']
      }),
      commonjs(),

      copy({
        targets: [
          { src: 'src/frontend/app/index.html', dest: 'public/app' }
        ],
        verbose: true
      }),

      production && terser()
    ],
    watch: {
      clearScreen: false
    }
  }
];
