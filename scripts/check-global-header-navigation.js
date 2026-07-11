const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', 'frontend');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function assertIncludes(file, needle) {
  const source = read(file);
  if (!source.includes(needle)) {
    throw new Error(`${file} must include ${needle}`);
  }
}

function assertNotIncludes(file, needle) {
  const source = read(file);
  if (source.includes(needle)) {
    throw new Error(`${file} must not include ${needle}`);
  }
}

assertIncludes('App.tsx', 'function AppHeader');
assertIncludes('App.tsx', 'function SearchPanel');
assertIncludes('App.tsx', 'function SharedResearchPanel');
assertIncludes('App.tsx', 'const handleSubmitSearch');
assertIncludes('App.tsx', 'const handleToggleSearch');
assertIncludes('App.tsx', "setCurrentScreen('home')");
assertIncludes('App.tsx', 'pendingSearchQuery');
assertIncludes('App.tsx', 'researchSnapshot');
assertIncludes('App.tsx', 'selectedStockCode');
assertIncludes('App.tsx', '<AppHeader');
assertIncludes('App.tsx', '<SearchPanel');
assertIncludes('App.tsx', '<SharedResearchPanel');
assertIncludes('App.tsx', "currentScreen !== 'login-settings'");
assertIncludes('App.tsx', 'onResearchSnapshotChange={setResearchSnapshot}');
assertIncludes('App.tsx', 'selectedStockCode={selectedStockCode}');

assertIncludes('src/pages/HomeScreen.tsx', 'pendingSearchQuery?: string | null');
assertIncludes('src/pages/HomeScreen.tsx', 'selectedStockCode?: string');
assertIncludes('src/pages/HomeScreen.tsx', 'onSelectedStockCodeChange?: (stockCode: string) => void');
assertIncludes('src/pages/HomeScreen.tsx', 'onResearchSnapshotChange?: (snapshot: ResearchSnapshot) => void');
assertIncludes('src/pages/HomeScreen.tsx', 'useEffect(() =>');
assertIncludes('src/pages/HomeScreen.tsx', 'void loadStocks(pendingSearchQuery)');
assertIncludes('src/pages/HomeScreen.tsx', 'void loadStockDetail(selectedStockCode)');
assertNotIncludes('src/pages/HomeScreen.tsx', 'const [isSearchVisible, setIsSearchVisible]');
assertNotIncludes('src/pages/HomeScreen.tsx', 'const [searchQuery, setSearchQuery]');
assertNotIncludes('src/pages/HomeScreen.tsx', 'style={styles.heroPanel}');
assertNotIncludes('src/pages/HomeScreen.tsx', 'style={styles.searchPanel}');

assertIncludes('src/pages/StockDetailScreen.tsx', 'onBack');
assertIncludes('src/pages/StockDetailScreen.tsx', 'onResearchSnapshotChange?: (snapshot: ResearchSnapshot) => void');
assertIncludes('src/pages/StockDetailScreen.tsx', 'onResearchSnapshotChange({');
assertNotIncludes('src/pages/StockDetailScreen.tsx', 'style={styles.heroPanel}');
assertNotIncludes('src/pages/StockDetailScreen.tsx', 'heroSummary');
assertNotIncludes('src/pages/StockDetailScreen.tsx', 'updateTime');

assertIncludes('src/types/index.ts', 'export interface ResearchSnapshot');
