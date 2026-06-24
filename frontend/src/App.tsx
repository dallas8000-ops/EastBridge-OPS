import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import OverviewPage from './pages/OverviewPage'
import RegulatoryPage from './pages/RegulatoryPage'
import PlaybooksPage from './pages/PlaybooksPage'
import VendorsPage from './pages/VendorsPage'
import IntelligencePage from './pages/IntelligencePage'
import AssistantPage from './pages/AssistantPage'
import AlertsPage from './pages/AlertsPage'
import TradePage from './pages/TradePage'
import LoginPage from './pages/LoginPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="regulatory" element={<RegulatoryPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="playbooks" element={<PlaybooksPage />} />
          <Route path="trade" element={<TradePage />} />
          <Route path="vendors" element={<VendorsPage />} />
          <Route path="intelligence" element={<IntelligencePage />} />
          <Route path="assistant" element={<AssistantPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
