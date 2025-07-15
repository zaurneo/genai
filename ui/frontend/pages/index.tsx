import ChatInterface from '../components/ChatInterface';

export default function Home() {
  const agentEndpoint = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  
  return <ChatInterface agentEndpoint={agentEndpoint} />;
}