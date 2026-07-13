import Link from 'next/link';
import { Sparkles, Zap, Globe } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-purple-50 to-white text-gray-900 font-sans">
      <header className="flex justify-between items-center p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold tracking-tight">Habib Audio Studio</h1>
        <div className="flex items-center gap-4 text-sm font-medium">
          <button className="hover:text-purple-600 transition">Buy Me Coffee</button>
          <Link href="/studio" className="bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition">
            Get Started
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 pt-20 pb-32">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <h2 className="text-5xl md:text-6xl font-extrabold leading-tight">
              Transform text <br /> into <span className="text-gray-500">lifelike</span> <br /> speech in seconds.
            </h2>
            <p className="text-gray-600 text-lg max-w-md">
              Experience the next generation of AI-powered voice synthesis. Create professional audio content with unmatched naturalness and emotion.
            </p>
            <div className="flex gap-4 pt-4">
              <Link href="/studio" className="bg-black text-white px-6 py-3 rounded-lg font-medium hover:bg-gray-800 transition">
                Get Started for Free →
              </Link>
            </div>
          </div>
          
          <div className="bg-white/60 backdrop-blur-sm border border-gray-200 p-4 rounded-2xl shadow-xl h-80 flex items-end justify-center pb-8">
             <span className="text-sm text-gray-500 font-medium">Generating High-Fidelity Audio...</span>
          </div>
        </div>

        <div className="mt-32 text-center">
          <h3 className="text-2xl font-bold mb-12">Professional Tools for Audio Excellence</h3>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-white p-8 rounded-2xl border border-gray-100 text-left shadow-sm">
              <div className="bg-purple-100 text-purple-700 w-10 h-10 rounded-lg flex items-center justify-center mb-6">
                <Sparkles size={20} />
              </div>
              <h4 className="text-lg font-bold mb-2">Human-Like Voices</h4>
              <p className="text-gray-500 text-sm">Access 5+ voices with deep emotional resonance.</p>
            </div>
            <div className="bg-white p-8 rounded-2xl border border-gray-100 text-left shadow-sm">
              <div className="bg-purple-100 text-purple-700 w-10 h-10 rounded-lg flex items-center justify-center mb-6">
                <Zap size={20} />
              </div>
              <h4 className="text-lg font-bold mb-2">Instant Synthesis</h4>
              <p className="text-gray-500 text-sm">Generate high-fidelity audio streams in milliseconds.</p>
            </div>
            <div className="bg-white p-8 rounded-2xl border border-gray-100 text-left shadow-sm">
              <div className="bg-purple-100 text-purple-700 w-10 h-10 rounded-lg flex items-center justify-center mb-6">
                <Globe size={20} />
              </div>
              <h4 className="text-lg font-bold mb-2">Global Reach</h4>
              <p className="text-gray-500 text-sm">Support for 100+ languages and localized accents.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}