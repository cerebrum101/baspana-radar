export default function Home() {
  return (
    <main>
      <h1>Какую квартиру купить в Астане?</h1>
      <p className="sub">
        Заполните форму — получите квартиры, ранжированные под ваши приоритеты,
        с прозрачным расчётом цены и рисков по каждому ЖК.
      </p>
      <form className="card" action="/results" method="GET">
        <div className="row">
          <div className="field">
            <label htmlFor="budget">Бюджет, млн ₸</label>
            <input id="budget" name="budget" type="number" min="10" max="500" defaultValue="42" />
          </div>
          <div className="field">
            <label htmlFor="rooms">Комнат</label>
            <select id="rooms" name="rooms" defaultValue="2">
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="district">Район</label>
            <select id="district" name="district" defaultValue="any">
              <option value="any">Любой</option>
              <option value="Есильский">Есильский</option>
              <option value="Нура">Нура</option>
              <option value="Сарайшык">Сарайшык</option>
            </select>
          </div>
        </div>
        <div className="row" style={{ marginTop: 14 }}>
          <div className="field">
            <label htmlFor="purpose">Цель покупки</label>
            <select id="purpose" name="purpose" defaultValue="live">
              <option value="live">Жить самому</option>
              <option value="invest">Инвестиция / сдача в аренду</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="risk">Отношение к риску</label>
            <select id="risk" name="risk" defaultValue="0.5">
              <option value="0">Осторожный — риски важнее цены</option>
              <option value="0.5">Сбалансированный</option>
              <option value="1">Толерантный — ищу недооценку</option>
            </select>
          </div>
        </div>
        <button className="primary" type="submit">Подобрать квартиры</button>
      </form>
      <p className="disclaimer">
        Demo-версия на срезе данных. Информация не является финансовой или
        юридической консультацией. Все оценки сопровождаются источниками и
        уровнем достоверности.
      </p>
    </main>
  );
}
