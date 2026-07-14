import "./globals.css";

export const metadata = {
  title: "Baspana Radar — честная цена на квартиры в Астане",
  description:
    "Оценка справедливой цены квартир в Астане по 26 000+ объявлений: где просят ниже рынка, статистика по ЖК и риск застройщика.",
  metadataBase: new URL("https://baspana-radar.example"),
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru">
      <body>
        <header className="site">
          <div className="wrap head">
            <a className="logo" href="/">
              <span className="dot" />Baspana Radar
            </a>
            <span className="tag">честная цена на квартиры в Астане</span>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
