/** Run Dashboard — four-panel diagnosis view for a single run. */
export default function RunDashboard({ params }: { params: { id: string } }) {
  return <main><h1>Run: {params.id}</h1></main>;
}
