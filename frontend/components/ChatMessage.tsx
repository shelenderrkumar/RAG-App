// app/components/ChatMessage.tsx
interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
}

export const ChatMessage = ({ role, content }: ChatMessageProps) => {
  const isUser = role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[70%] rounded-lg px-4 py-2 ${
        isUser ? 'bg-blue-500 text-white' : 'bg-gray-200'
      }`}>
        <p>{content}</p>
      </div>
    </div>
  );
};