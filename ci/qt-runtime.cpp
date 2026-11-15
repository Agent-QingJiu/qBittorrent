#include <QCoreApplication>
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QSslSocket>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (!QSslSocket::supportsSsl())
        return 1;

    auto database = QSqlDatabase::addDatabase("QSQLITE");
    database.setDatabaseName(":memory:");
    if (!database.open())
        return 2;

    QSqlQuery query;
    return query.exec("SELECT 1") && query.next() && query.value(0).toInt() == 1 ? 0 : 3;
}
