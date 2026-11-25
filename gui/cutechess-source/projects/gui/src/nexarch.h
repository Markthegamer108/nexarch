// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Mark Ivanovskyy

#ifndef NEXARCH_H
#define NEXARCH_H

#include <QDialog>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QStringList>
#include <QTimer>
#include <chessplayer.h>
#include <playerbuilder.h>

class QCheckBox;
class QComboBox;
class QLabel;
class QLineEdit;
class QPushButton;
class QNetworkReply;
class QSlider;
class QTableWidget;

class RemotePlayer : public ChessPlayer
{
	Q_OBJECT

	public:
		explicit RemotePlayer(QObject* parent = nullptr);
		virtual void endGame(const Chess::Result& result);
		virtual void makeMove(const Chess::Move& move);
		virtual bool supportsVariant(const QString& variant) const;
		virtual bool isHuman() const;

	public slots:
		void receiveMove(const QString& uci);
		void receiveMoves(const QStringList& moves);

	protected:
		virtual void startGame();
		virtual void startThinking();

	private:
		Chess::Move m_buffer;
};

class RemoteBuilder : public PlayerBuilder
{
	public:
		explicit RemoteBuilder(const QString& name);
		virtual bool isHuman() const;
		virtual ChessPlayer* create(QObject* receiver,
					    const char* method,
					    QObject* parent,
					    QString* error) const;
};

class NexarchOnline : public QObject
{
	Q_OBJECT

	public:
		explicit NexarchOnline(QObject* parent = nullptr);
		void createRoom(const QString& server, const QString& name, const QString& color);
		void joinRoom(const QString& server, const QString& name, const QString& room);
		void startPolling();
		void stopPolling();
		QString server() const;
		QString room() const;
		QString token() const;
		QString color() const;
		QString playerName() const;
		QString opponentName() const;
		QStringList initialMoves() const;
		int initialCount() const;

	public slots:
		void sendMove(const QString& uci);
		void reportResult(const QString& result);

	signals:
		void ready();
		void failed(const QString& message);
		void status(const QString& text);
		void movesReceived(const QStringList& moves);
		void gameOver(const QString& result);

	private slots:
		void poll();
		void handleRoom();
		void handleMove();
		void handleState();

	private:
		void post(const QString& path, const QJsonObject& body, const char* slot);
		void applyState(const QJsonObject& state, bool initial);
		QString base() const;

		QNetworkAccessManager m_net;
		QTimer m_timer;
		QString m_server;
		QString m_room;
		QString m_token;
		QString m_color;
		QString m_name;
		QString m_opponent;
		QStringList m_initialMoves;
		int m_count;
		bool m_polling;
};

class NexarchOnlineDialog : public QDialog
{
	Q_OBJECT

	public:
		explicit NexarchOnlineDialog(QWidget* parent = nullptr);
		NexarchOnline* takeOnline();
		QString color() const;
		QStringList initialMoves() const;
		int initialCount() const;

	private slots:
		void createRoom();
		void joinRoom();
		void onReady();
		void onFailed(const QString& message);

	private:
		NexarchOnline* m_online;
		QLineEdit* m_server;
		QLineEdit* m_name;
		QLineEdit* m_room;
		QComboBox* m_color;
		QLabel* m_status;
		QPushButton* m_create;
		QPushButton* m_join;
		QString m_chosenColor;
};

class NexarchRankingsDialog : public QDialog
{
	Q_OBJECT

	public:
		explicit NexarchRankingsDialog(QWidget* parent = nullptr);

	private slots:
		void loadLichess();
		void loadChessCom();
		void lichessReply();
		void chessComReply();

	private:
		QNetworkAccessManager m_net;
		QTableWidget* m_table;
		QLabel* m_status;
};

class NexarchSettingsDialog : public QDialog
{
	Q_OBJECT

	public:
		explicit NexarchSettingsDialog(QWidget* parent = nullptr);

	private slots:
		void save();

	private:
		QCheckBox* m_telemetry;
		QSlider* m_strength;
		QLabel* m_strengthLabel;
};

class NexarchCreditsDialog : public QDialog
{
	Q_OBJECT

	public:
		explicit NexarchCreditsDialog(QWidget* parent = nullptr);
};

namespace Nexarch
{
	QString telemetryUrl();
	bool telemetryEnabled();
	void setTelemetryEnabled(bool enabled);
	int strength();
	void setStrength(int elo);
	void applyStrength();
	void sendGame(const QString& pgn, const QString& result);
}

#endif
