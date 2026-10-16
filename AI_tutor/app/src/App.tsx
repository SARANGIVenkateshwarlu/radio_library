import { Routes, Route } from 'react-router'
import Home from './pages/Home'
import Chat from './pages/Chat'
import Drill from './pages/Drill'
import Review from './pages/Review'
import Phrasebook from './pages/Phrasebook'
import Resources from './pages/Resources'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/chat/:id" element={<Chat />} />
      <Route path="/drill/:id" element={<Drill />} />
      <Route path="/review" element={<Review />} />
      <Route path="/phrasebook" element={<Phrasebook />} />
      <Route path="/resources" element={<Resources />} />
      <Route path="*" element={<Home />} />
    </Routes>
  )
}
