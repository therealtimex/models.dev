# Task: Implement a Dynamic Model Properties System

**ID:** `MOD-01`
**Priority:** CRITICAL
**Assignee:** `GeminiCLI`
**Status:** `Not Started`

## 1. Objective

To create a robust, performant, and resilient system for managing AI model capabilities. This system will fetch a pre-computed JSON file containing operational parameters (like context window, chunk size, etc.) for various models. This replaces any hardcoded or manually maintained model configurations within the application, making our app automatically adaptable to new and updated models.

The system will consist of two primary parts:
1.  **A Generation Script:** A server-side script that creates the master `model-properties.json` file.
2.  **An Application Module:** A lightweight client module inside our main application that fetches, caches, and provides these properties at runtime.

## 2. Background & Strategy

We are offloading complexity from our application's runtime to a build-time process. Our fork of `models.dev` will use a GitHub Action to run a script that scans all model `.toml` files, applies our custom heuristics, and generates a single `dist/model-properties.json`.

This generated file will be hosted via GitHub Pages at a stable URL:
`https://therealtimex.github.io/models.dev/dist/model-properties.json`

Your task is to build both the generation script and the application-side consumer module.

---

## 3. Implementation Steps

### Part A: The Generation Script (in `therealtimex/models.dev` repository)

#### Step A1: Setup Project and Dependencies
1.  In your local clone of the `therealtimex/models.dev` fork, initialize an npm project if one doesn't exist (`npm init -y`).
2.  Install the required development dependencies:
    ```bash
    npm install glob toml --save-dev
    ```

#### Step A2: Create the Generation Script
1.  Create a new file: `scripts/generate-properties.js`.
2.  Implement the script logic as detailed below. This script will be the "factory" for our properties file.

**`scripts/generate-properties.js`:**
```javascript
import { glob } from 'glob';
import { readFile, writeFile, mkdir } from 'fs/promises';
import path from 'path';
import TOML from 'toml';

// Centralized Heuristics Engine: Define application-specific logic here.
function deriveOperationalLimits(modelId, rawProps) {
  const context = rawProps.limit?.context ?? 4096;
  const output = rawProps.limit?.output ?? 1024;

  // Derive operational values from raw specs
  return {
    id: modelId,
    contextWindow: context,
    limits: {
      chunkSize: Math.floor(context * 0.75), // Use 75% of context for splitting
      summaryMaxTokens: Math.min(output, 4096), // Cap summaries at 4k for quality
      truncateThreshold: context < 8192 ? 1.5 : 1.25, // Heuristic for cheap truncation
    },
  };
}

async function generate() {
  const modelFiles = await glob('providers/**/*.toml');
  const modelProperties = {};

  for (const file of modelFiles) {
    try {
      const modelId = file.replace('providers/', '').replace('.toml', '');
      const content = await readFile(file, 'utf-8');
      const rawProps = TOML.parse(content);
      modelProperties[modelId] = deriveOperationalLimits(modelId, rawProps);
      console.log(`[SUCCESS] Processed: ${modelId}`);
    } catch (error) {
      console.error(`[ERROR] Failed to process ${file}:`, error.message);
    }
  }

  // Add a mandatory default fallback model
  modelProperties['default'] = {
    id: 'default',
    contextWindow: 4096,
    limits: { chunkSize: 3000, summaryMaxTokens: 1024, truncateThreshold: 1.5 },
  };

  const outputPath = path.join('dist', 'model-properties.json');
  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, JSON.stringify(modelProperties, null, 2));

  console.log(`\n✅ Generated model properties at ${outputPath}`);
}

generate();
```

#### Step A3: Test the Script
1.  Run the script locally to ensure it works correctly:
    ```bash
    node scripts/generate-properties.js
    ```
2.  Verify that `dist/model-properties.json` is created and contains the expected structured data.

---

### Part B: The Application Module (in the main application repository)

#### Step B1: Setup Dependencies
1.  In the main application, install the necessary packages:
    ```bash
    npm install node-cache node-fetch
    ```

#### Step B2: Create the Fallback File
1.  Copy the `dist/model-properties.json` file you generated in Part A.
2.  Place it inside the main application at `src/lib/fallback-model-properties.json`.
3.  **Commit this fallback file to the repository.** This is crucial for resilience.

#### Step B3: Create the Application Module
1.  Create a new file: `src/lib/model-properties.js`.
2.  Implement the module as a singleton class that fetches, caches, and provides the properties.

**`src/lib/model-properties.js`:**
```javascript
import fetch from 'node-fetch';
import NodeCache from 'node-cache';
import fs from 'fs/promises';
import path from 'path';

const PROPERTIES_URL = 'https://therealtimex.github.io/models.dev/dist/model-properties.json';
const FALLBACK_PATH = path.join(process.cwd(), 'src', 'lib', 'fallback-model-properties.json');
const cache = new NodeCache({ stdTTL: 3600 }); // 1-hour cache

class ModelProperties {
  #properties = null;
  #isInitialized = false;

  // Initialize fetches remote properties, with a fallback to a local file
  async initialize() {
    if (this.#isInitialized) return;

    try {
      const cachedProps = cache.get('model-properties');
      if (cachedProps) {
        this.#properties = cachedProps;
        console.log('Loaded model properties from cache.');
      } else {
        console.log('Fetching fresh model properties...');
        const response = await fetch(PROPERTIES_URL);
        if (!response.ok) throw new Error(`Fetch failed with status ${response.status}`);
        const remoteProps = await response.json();
        this.#properties = remoteProps;
        cache.set('model-properties', remoteProps);
        console.log('Successfully fetched and cached model properties.');
      }
    } catch (error) {
      console.warn(`[WARN] Could not fetch remote model properties: ${error.message}. Using fallback.`);
      try {
        const fallbackData = await fs.readFile(FALLBACK_PATH, 'utf-8');
        this.#properties = JSON.parse(fallbackData);
      } catch (fallbackError) {
        console.error('[FATAL] Could not load fallback properties. The application may be unstable.', fallbackError);
        this.#properties = { default: { id: 'default', contextWindow: 4096, limits: { chunkSize: 3000, summaryMaxTokens: 1024, truncateThreshold: 1.5 } } };
      }
    }
    this.#isInitialized = true;
  }

  // The main public API for the rest of your app
  getProperties(modelId = 'default') {
    if (!this.#isInitialized) {
      // This is a safeguard. The application should `await initialize()` at startup.
      throw new Error('ModelProperties not initialized. Please await initialize() on app startup.');
    }
    // Return the specific model's properties or the default if not found
    return this.#properties[modelId] || this.#properties.default;
  }
}

// Export a singleton instance so initialization runs only once.
const modelPropertiesInstance = new ModelProperties();
export default modelPropertiesInstance;
```

#### Step B4: Integrate into Application Startup
1.  In your application's main entry point (e.g., `index.js`, `app.js`), ensure you `await` the initialization of this module before starting the server or processing requests.

```javascript
// In your main application startup file (e.g., app.js)
import modelProperties from './src/lib/model-properties.js';

async function startApp() {
  // IMPORTANT: Initialize model properties before doing anything else
  await modelProperties.initialize();
  console.log('Application is ready to serve requests.');

  // ... rest of your server setup ...
}

startApp();
```

## 4. Acceptance Criteria

-   [ ] The `generate-properties.js` script successfully creates a valid `dist/model-properties.json` file.
-   [ ] The `model-properties.js` module in the main app successfully fetches and caches the remote JSON file.
-   [ ] If the remote fetch fails, the module successfully loads the `fallback-model-properties.json` without crashing.
-   [ ] Calling `modelProperties.getProperties('openai/gpt-4-turbo')` returns the correct, structured object for that model.
-   [ ] Calling `modelProperties.getProperties('non-existent-model')` returns the `default` model properties.
-   [ ] The application startup sequence correctly awaits the initialization of the `ModelProperties` module.