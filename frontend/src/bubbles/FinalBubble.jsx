export default function FinalBubble({ message, onAction }) {
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = message.src;
    link.download = 'final_image.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="final-bubble">
      <div className="final-header">Your image is ready!</div>
      <img src={message.src} alt="Final image" className="final-image" />
      <div className="final-actions">
        <button className="final-download" onClick={handleDownload}>
          Download Image
        </button>
        <button
          className="final-restart"
          onClick={() => onAction({ decision: 'reject' })}
        >
          Start Over
        </button>
      </div>
    </div>
  );
}
