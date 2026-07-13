import "./globals.css";
import Link from "next/link";
import { SNAPSHOT_DATE } from "../lib/data";

export const metadata = {
  title: "Baspana Radar — независимый советник по недвижимости Астаны",
  description:
    "Оценка квартир, анализ ЖК и карточки due diligence по Астане: цены, риски, источники.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru">
      <body>
        <header className="site">
          <div className="inner">
            <Link href="/" className="logo">
              Baspana<span>Radar</span>
            </Link>
            <span className="snapshot">
              срез данных: {SNAPSHOT_DATE} · demo
            </span>
          </div>
        </header>
        <div className="container">{children}</div>
      </body>
    </html>
  );
}
